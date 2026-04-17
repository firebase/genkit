# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Registry for managing Genkit resources and actions."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, cast

from dotpromptz.dotprompt import Dotprompt
from pydantic import BaseModel
from typing_extensions import Never, TypeVar

from genkit._core._action import (
    GENKIT_DYNAMIC_ACTION_PROVIDER_ATTR,
    Action,
    ActionKind,
    ActionMetadata,
    ActionName,
    ActionRunContext,
    SpanAttributeValue,
    create_action_key,
    parse_action_key,
    parse_dap_qualified_name,
)
from genkit._core._logger import get_logger
from genkit._core._model import (
    ModelRequest,
    ModelResponse,
    ModelResponseChunk,
)
from genkit._core._plugin import Plugin
from genkit._core._typing import (
    EmbedRequest,
    EmbedResponse,
    EvalRequest,
    EvalResponse,
)

logger = get_logger(__name__)

# An action store is a nested dictionary mapping ActionKind to a dictionary of
# action names and their corresponding Action instances.
#
# Structure for illustration:
#
# ```python
# {
#     ActionKind.MODEL: {
#         'gemini-2.0-flash': Action(...),
#         'gemini-2.0-pro': Action(...)
#     },
# }
# ```
ActionStore = dict[ActionKind, dict[ActionName, Action]]

InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')
ChunkT = TypeVar('ChunkT', default=Never)

ActionFn = (
    Callable[[], OutputT | Awaitable[OutputT]]
    | Callable[[InputT], OutputT | Awaitable[OutputT]]
    | Callable[[InputT, ActionRunContext], OutputT | Awaitable[OutputT]]
)


def _reflection_payload_for_registered_action(action: Action) -> dict[str, Any]:
    key = create_action_key(action.kind, action.name)
    return {
        'key': key,
        'name': action.name,
        'type': action.kind,
        'description': action.description,
        'inputSchema': action.input_schema,
        'outputSchema': action.output_schema,
        'metadata': action.metadata,
    }


def _reflection_payload_for_plugin_metadata(meta: ActionMetadata) -> dict[str, Any]:
    key = f'/{meta.kind}/{meta.name}'
    return {
        'key': key,
        'name': meta.name,
        'type': meta.kind,
        'description': meta.description,
        'inputSchema': meta.input_json_schema,
        'outputSchema': meta.output_json_schema,
        'metadata': meta.metadata,
    }


def _reflection_payload_for_dap_metadata(full_key: str, meta: Mapping[str, object]) -> dict[str, Any]:
    return {
        'key': full_key,
        'name': meta.get('name'),
        'type': meta.get('type'),
        'description': meta.get('description'),
        'inputSchema': meta.get('inputSchema') or meta.get('input_json_schema'),
        'outputSchema': meta.get('outputSchema') or meta.get('output_json_schema'),
        'metadata': dict(meta),
    }


class Registry:
    """Central repository for Genkit resources.

    The Registry class serves as the central storage and management system for
    various Genkit resources including actions, trace stores, flow state stores,
    plugins, and schemas. It provides methods for registering new resources and
    looking them up at runtime.

    Supports a **child registry** pattern (see ``new_child``): a child registry
    delegates lookups to its parent when a name is not found locally.  This is
    used to create cheap, ephemeral registries scoped to a single generate call
    (for DAP-resolved tools) without polluting the root registry.

    This class is thread-safe and can be safely shared between multiple threads.

    Attributes:
        entries: A nested dictionary mapping ActionKind to a dictionary of
            action names and their corresponding Action instances.
    """

    def __init__(self, parent: Registry | None = None) -> None:
        """Initialize a Registry instance.

        Args:
            parent: Optional parent registry.  When provided this is a *child*
                registry that falls back to the parent for any lookup that
                returns ``None`` locally.  Use ``new_child()`` as the
                preferred factory rather than passing ``parent`` directly.
        """
        self._parent: Registry | None = parent
        self._default_model: str | None = None
        self._entries: ActionStore = {}
        self._value_by_kind_and_name: dict[str, dict[str, object]] = {}
        self._schemas_by_name: dict[str, dict[str, object]] = {}
        self._schema_types_by_name: dict[str, type[BaseModel]] = {}
        self._lock: threading.RLock = threading.RLock()

        # Re-entrancy guard for _trigger_lazy_loading.  Prevents infinite
        # recursion when a lazy factory resolves its own action key (see
        # https://github.com/firebase/genkit/issues/4491).
        self._loading_actions: set[str] = set()

        # Dotprompt resolves ``output.schema`` names via the registry's stored schemas.
        # Async resolver avoids thread-pool deadlock in ``resolve_json_schema``.
        async def async_schema_resolver(name: str) -> dict[str, object] | str:
            return self.lookup_schema(name) or name

        # Children share the parent's Dotprompt instance (prompts are global).
        self.dotprompt: Dotprompt = (
            parent.dotprompt if parent is not None else Dotprompt(schema_resolver=async_schema_resolver)
        )
        # TODO(#4352): Figure out how to set this.
        self.api_stability: str = 'stable'

        # Plugin infrastructure
        #
        # Notes on concurrency:
        # - Registry state is protected by the thread lock (`_lock`) because the dev
        #   reflection server runs in a separate OS thread and inspects the same
        #   registry instance.
        # - Plugin initialization is lazy and "init-once" via an in-flight task
        #   cache (`_plugin_init_tasks`). This assumes a single asyncio event loop
        #   drives plugin initialization for a given registry instance. (The dev
        #   reflection server schedules coroutines onto that loop.)
        self._plugins: dict[str, Plugin] = {}
        self._plugin_init_tasks: dict[str, asyncio.Task[None]] = {}
        self._all_plugins_initialized: bool = False

    # -------------------------------------------------------------------------
    # Child registry support
    # -------------------------------------------------------------------------

    def new_child(self) -> Registry:
        """Create a cheap child registry that inherits from this registry.

        Child registries are used to create short-lived, ephemeral scopes (e.g.
        per-generate-call tool registrations from a DAP) without polluting the
        root registry.  Any lookup that fails locally falls back to this parent.
        Writes on the child never propagate back to the parent.

        Returns:
            A new ``Registry`` whose parent is ``self``.
        """
        return Registry(parent=self)

    @property
    def parent(self) -> Registry | None:
        """The parent registry, or ``None`` if this is a root registry."""
        return self._parent

    @property
    def is_child(self) -> bool:
        """``True`` if this registry has a parent."""
        return self._parent is not None

    @property
    def default_model(self) -> str | None:
        """The default model name, falling back to parent if not set locally."""
        if self._default_model is not None:
            return self._default_model
        return self._parent.default_model if self._parent is not None else None

    @default_model.setter
    def default_model(self, value: str | None) -> None:
        self._default_model = value

    def register_action(
        self,
        kind: ActionKind,
        name: str,
        fn: ActionFn[InputT, OutputT],
        metadata_fn: Callable[..., object] | None = None,
        description: str | None = None,
        metadata: dict[str, object] | None = None,
        span_metadata: dict[str, SpanAttributeValue] | None = None,
    ) -> Action[InputT, OutputT, ChunkT]:
        """Register a new action with the registry.

        This method creates a new Action instance with the provided parameters
        and registers it in the registry under the specified kind and name.

        Args:
            kind: The type of action being registered (e.g., TOOL, MODEL).
            name: A unique name for the action within its kind.
            fn: The function to be called when the action is executed.
            metadata_fn: The function to be used to infer metadata (e.g.
                schemas).
            description: Optional human-readable description of the action.
            metadata: Optional dictionary of metadata about the action.
            span_metadata: Optional dictionary of tracing span metadata.

        Returns:
            The newly created and registered Action instance.
        """
        action = Action(
            kind=kind,
            name=name,
            fn=cast(Callable[..., Awaitable[OutputT]], fn),
            metadata_fn=metadata_fn,
            description=description,
            metadata=metadata,
            span_metadata=span_metadata,
        )
        action_typed = cast(Action[InputT, OutputT, ChunkT], action)
        with self._lock:
            if kind not in self._entries:
                self._entries[kind] = {}
            self._entries[kind][name] = action
        return action_typed

    def register_action_from_instance(self, action: Action) -> None:
        """Register an existing Action instance.

        Allows registering a pre-configured Action object, such as one created via
        `dynamic_resource` or other factory methods.

        Args:
           action: The action instance to register.
        """
        with self._lock:
            if action.kind not in self._entries:
                self._entries[action.kind] = {}
            self._entries[action.kind][action.name] = action

    async def resolve_actions_by_kind(self, kind: ActionKind) -> dict[str, Action]:
        """Returns all registered actions for a specific kind, triggering lazy loading.

        File-based prompts defer schema resolution until first access. This method
        ensures all action metadata is fully loaded before returning.

        Args:
            kind: The type of actions to retrieve (e.g., TOOL, MODEL, RESOURCE).

        Returns:
            A dictionary mapping action names to Action instances with fully loaded metadata.
        """
        with self._lock:
            actions = self._entries.get(kind, {}).copy()
        for action in actions.values():
            await self._trigger_lazy_loading(action)
        return actions

    async def list_actions(self) -> dict[str, Action]:
        """Return every concrete :class:`Action` in ``_entries``, keyed by ``/<kind>/<name>``.

        Ensures plugins are initialized first so ``init()``-registered actions appear.
        Merges with the parent registry when present; on duplicate keys the child wins.
        For advertised-only and DAP-expanded metadata (reflection catalog), use
        :meth:`list_resolvable_actions`.

        Returns:
            Map of action key string to :class:`Action` instance.
        """
        await self.initialize_all_plugins()
        local: dict[str, Action] = {}
        for kind in ActionKind.__members__.values():
            for name, action in (await self.resolve_actions_by_kind(kind)).items():
                local[create_action_key(kind, name)] = action
        if self._parent is None:
            return local
        parent_actions = await self._parent.list_actions()
        return {**parent_actions, **local}

    async def list_resolvable_actions(self) -> dict[str, dict[str, Any]]:
        """Return reflection metadata for plugins, registered actions, and DAP-expanded tools.

        Builds plugin rows from each plugin's ``list_actions()``, then fills registered
        actions and DAP expansions via :meth:`list_actions` (which initializes plugins).
        Merges with parent's list_resolvable_actions() output (prefer child entries on duplicate keys).

        Returns:
            Map of action key to reflection-style payload dicts (``key``, ``name``, ``type``, etc.).
        """
        local: dict[str, dict[str, Any]] = {}

        with self._lock:
            plugins = list(self._plugins.items())
        for plugin_name, plugin in plugins:
            try:
                plugin_metas = await plugin.list_actions()
            except Exception:
                logger.exception('Error listing actions for plugin %s', plugin_name)
                continue
            for meta in plugin_metas or []:
                if not meta.name:
                    raise ValueError(f'Invalid ActionMetadata from {plugin_name}: name required')
                if '/' not in meta.name:
                    meta = meta.model_copy(update={'name': f'{plugin_name}/{meta.name}'})
                key = f'/{meta.kind}/{meta.name}'
                local[key] = _reflection_payload_for_plugin_metadata(meta)

        actions_dict = await self.list_actions()
        actions = actions_dict.items()
        for key, action in actions:
            local[key] = _reflection_payload_for_registered_action(action)
            dap = getattr(action, GENKIT_DYNAMIC_ACTION_PROVIDER_ATTR, None)
            if dap is None:
                continue
            try:
                # Record keys use the provider action ``name``; see
                # :meth:`DynamicActionProvider.get_action_metadata_record`.
                record = await dap.get_action_metadata_record(action.name)
            except Exception:
                logger.exception(
                    'Error listing actions for Dynamic Action Provider %s',
                    action.name,
                )
                continue
            for record_key, meta in record.items():
                full_key = create_action_key(ActionKind.DYNAMIC_ACTION_PROVIDER, record_key)
                local[full_key] = _reflection_payload_for_dap_metadata(full_key, meta)
                parts = parse_dap_qualified_name(record_key)
                if parts is None:
                    continue
                _provider, inner_kind_str, inner_name = parts
                try:
                    inner_kind = ActionKind(inner_kind_str)
                except ValueError:
                    logger.debug(
                        "Unrecognized ActionKind '%s' in DAP record key '%s' from provider '%s'",
                        inner_kind_str,
                        record_key,
                        action.name,
                    )
                    continue

                canonical = create_action_key(inner_kind_str, inner_name)
                if canonical in local:
                    continue
                try:
                    nested = await dap.get_action(inner_kind_str, inner_name)
                except Exception as e:
                    logger.debug(
                        'DAP %s failed resolving nested action %s/%s for canonical catalog row',
                        action.name,
                        inner_kind_str,
                        inner_name,
                        exc_info=e,
                    )
                    nested = None
                if nested is not None:
                    local[canonical] = _reflection_payload_for_registered_action(nested)
                else:
                    canon_payload = dict(_reflection_payload_for_dap_metadata(full_key, meta))
                    canon_payload['key'] = canonical
                    canon_payload['name'] = inner_name
                    canon_payload['type'] = inner_kind
                    local[canonical] = canon_payload

        if self._parent is None:
            return local
        parent_resolvable = await self._parent.list_resolvable_actions()
        return {**parent_resolvable, **local}

    def register_value(self, kind: str, name: str, value: object) -> None:
        """Registers a value with a given kind and name.

        This method stores a value in a nested dictionary, where the first level
        is keyed by the 'kind' and the second level is keyed by the 'name'.
        It prevents duplicate registrations for the same kind and name.

        Args:
            kind: The kind of the value (e.g., "format", "default-model").
            name: The name of the value (e.g., "json", "text").
            value: The value to be registered. Can be of any non-serializable
                type.

        Raises:
            ValueError: If a value with the given kind and name is already
            registered.
        """
        with self._lock:
            if kind not in self._value_by_kind_and_name:
                self._value_by_kind_and_name[kind] = {}

            if name in self._value_by_kind_and_name[kind]:
                raise ValueError(f'value for kind "{kind}" and name "{name}" is already registered')

            self._value_by_kind_and_name[kind][name] = value

    def lookup_value(self, kind: str, name: str) -> object | None:
        """Looks up value that us previously registered by `register_value`.

        Args:
            kind: The kind of the value (e.g., "format", "default-model").
            name: The name of the value (e.g., "json", "text").

        Returns:
            The value or None if not found.  Falls back to parent registry.
        """
        with self._lock:
            local = self._value_by_kind_and_name.get(kind, {}).get(name)
        if local is not None:
            return local
        return self._parent.lookup_value(kind, name) if self._parent is not None else None

    def list_values(self, kind: str) -> list[str]:
        """List all values registered for a specific kind.

        Args:
            kind: The kind of values to list (e.g., "defaultModel").

        Returns:
            A list of registered value names.
        """
        with self._lock:
            return list(self._value_by_kind_and_name.get(kind, {}).keys())

    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin with the registry.

        Args:
            plugin: The plugin to register.

        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        # Guard plugin registry mutations: in dev mode the reflection server may
        # list actions while the main thread is still registering plugins.
        with self._lock:
            if plugin.name in self._plugins:
                raise ValueError(f'Plugin {plugin.name} already registered')
            self._plugins[plugin.name] = plugin
            self._all_plugins_initialized = False

    async def initialize_all_plugins(self) -> None:
        """Run ``init()`` for every plugin on this registry exactly once (until a new plugin is registered).

        Used before enumerating registered actions so plugin-registered entries exist in ``_entries``.
        """
        if self._all_plugins_initialized:
            return
        with self._lock:
            plugin_names = list(self._plugins.keys())
        for name in plugin_names:
            await self._ensure_plugin_initialized(name)
        self._all_plugins_initialized = True

    async def _ensure_plugin_initialized(self, plugin_name: str) -> None:
        """Ensure a plugin is initialized exactly once.

        This method implements lazy, once-only initialization using an in-flight
        task pattern. Multiple concurrent calls will await the same task.

        Args:
            plugin_name: The name of the plugin to initialize.

        Raises:
            KeyError: If the plugin is not registered.
        """
        # IMPORTANT: Do not hold `_lock` across any `await`. The critical section
        # below is sync-only (dict access + task creation), so it is safe to use
        # `_lock` to make the init-once behavior atomic across threads/tasks.
        with self._lock:
            task = self._plugin_init_tasks.get(plugin_name)
            if task is None:
                plugin = self._plugins.get(plugin_name)
                if plugin is None:
                    raise KeyError(f'Plugin not registered: {plugin_name}')

                async def run_init() -> None:
                    # Assert for type narrowing inside closure (pyrefly doesn't propagate from outer scope)
                    assert plugin is not None
                    actions = await plugin.init()
                    for action in actions or []:
                        self.register_action_instance(action, namespace=plugin_name)

                task = asyncio.create_task(run_init())
                self._plugin_init_tasks[plugin_name] = task

        await task

    def register_action_instance(self, action: Action, *, namespace: str | None = None) -> None:
        """Register an existing Action instance with optional namespace normalization.

        If a namespace is provided, the action name will be normalized to ensure
        it has the correct plugin prefix.

        Args:
            action: The action instance to register.
            namespace: Optional plugin namespace to prefix the action name.
        """
        name = action.name
        if namespace:
            if '/' in name:
                # Name already has a namespace, replace it
                _, local = name.split('/', 1)
                name = f'{namespace}/{local}'
            else:
                # Name is local, prefix with namespace
                name = f'{namespace}/{name}'
            # Update the action's name
            action._name = name  # pyright: ignore[reportPrivateUsage]

        with self._lock:
            if action.kind not in self._entries:
                self._entries[action.kind] = {}
            self._entries[action.kind][name] = action

    async def _trigger_lazy_loading(self, action: Action | None) -> Action | None:
        """Trigger lazy loading for an action if needed.

        File-based prompts are registered with deferred metadata (schemas). This method
        triggers the async factory to resolve that metadata before returning the action.
        The factory is memoized, so subsequent calls return immediately.

        A re-entrancy guard (``_loading_actions``) prevents infinite recursion
        when a factory resolves its own action key during initialization.
        See https://github.com/firebase/genkit/issues/4491.
        """
        if action is None:
            return None
        async_factory = getattr(action, '_async_factory', None)
        if async_factory is not None and action.metadata.get('lazy'):
            action_id = f'{action.kind}/{action.name}'
            if action_id in self._loading_actions:
                return action
            self._loading_actions.add(action_id)
            try:
                await async_factory()
            except Exception as e:
                logger.warning(f'Failed to load lazy action {action.name}: {e}')
            finally:
                self._loading_actions.discard(action_id)
        return action

    async def _resolve_dap_qualified_action(self, kind: ActionKind, name: str) -> Action | None:
        """Resolve through the one registered DAP for ``provider:innerKind/innerName`` names.

        Caller must ensure :func:`parse_dap_qualified_name` accepts ``name``. Does not consult
        plugins. Returns ``None`` if the provider is not registered here (caller may delegate
        to a parent registry).
        """
        qualified = parse_dap_qualified_name(name)
        if qualified is None:
            return None
        dap_host = qualified.provider
        with self._lock:
            provider = self._entries.get(ActionKind.DYNAMIC_ACTION_PROVIDER, {}).get(dap_host)
        if provider is None:
            return None
        dap_action = await self._trigger_lazy_loading(provider)
        if dap_action is None:
            raise RuntimeError(
                f'Dynamic action provider {dap_host!r} is not registered. '
                'DAPs must be registered using define_dynamic_action_provider '
                'before referencing qualified action names.'
            )
        dap = getattr(dap_action, GENKIT_DYNAMIC_ACTION_PROVIDER_ATTR, None)
        if dap is not None:
            try:
                resolved = await dap.get_action(qualified.inner_kind, qualified.inner_name)
            except Exception as e:
                raise ValueError(f'Dynamic action provider {dap_host!r} get_action failed for {kind} {name!r}') from e
            if resolved is not None and resolved.kind == kind:
                return resolved
            if resolved is None:
                raise ValueError(
                    f'Dynamic action provider {dap_host!r} has no action '
                    f'{qualified.inner_kind!r}/{qualified.inner_name!r} for {name!r}'
                )
            raise ValueError(
                f'Dynamic action provider {dap_host!r} returned {resolved.kind!r} for {name!r}, expected {kind!r}'
            )
        try:
            response = await dap_action.run({'kind': kind, 'name': name})
            if response.response:
                self.register_action_instance(response.response)
                return await self._trigger_lazy_loading(response.response)
        except Exception as e:
            logger.debug(
                f'Dynamic action provider {dap_host} failed for {kind}/{name}',
                exc_info=e,
            )
        return None

    async def resolve_action(self, kind: ActionKind, name: str) -> Action | None:
        """Resolve an action by kind and name.

        Tries an exact (kind, name) cache hit first. DAP-qualified names
        (provider:innerKind/innerName) go through that provider only. If the name contains a
        slash, the first segment is treated as a plugin id: that plugin is initialized and
        plugin.resolve is used. Falls back to parent registry if nothing found.

        Args:
            kind: The type of action to resolve.
            name: Action name, optionally plugin/... for a specific plugin.

        Returns:
            The Action instance if found, None otherwise.
        """
        with self._lock:
            if kind in self._entries and name in self._entries[kind]:
                return await self._trigger_lazy_loading(self._entries[kind][name])

        # DAP-qualified names: resolve via that provider only (not plugin slash splitting).
        if kind != ActionKind.DYNAMIC_ACTION_PROVIDER and parse_dap_qualified_name(name) is not None:
            action = await self._resolve_dap_qualified_action(kind, name)
            if action is not None:
                return action
            if self._parent is not None:
                return await self._parent.resolve_action(kind, name)
            return None

        # <plugin name>/<action name>: resolve that plugin.
        if '/' in name:
            plugin_name, action_name = name.split('/', 1)
            with self._lock:
                plugin = self._plugins.get(plugin_name)

            if plugin is not None:
                await self._ensure_plugin_initialized(plugin_name)

                target = f'{plugin_name}/{action_name}'  # normalized

                # Check cache again after init - init() might have registered this action
                with self._lock:
                    if kind in self._entries and target in self._entries[kind]:
                        return await self._trigger_lazy_loading(self._entries[kind][target])

                action = await plugin.resolve(kind, target)
                if action is not None:
                    self.register_action_instance(action, namespace=plugin_name)
                    with self._lock:
                        return await self._trigger_lazy_loading(self._entries.get(kind, {}).get(target))

        # Final fallback: delegate to parent registry.
        if self._parent is not None:
            return await self._parent.resolve_action(kind, name)

        return None

    async def resolve_action_by_key(self, key: str) -> Action | None:
        """Resolve an action using its combined key string.

        The key format is ``/<kind>/<name>``, where kind must be a valid
        ``ActionKind`` and name may be prefixed with plugin namespace or
        unprefixed.

        For nested actions exposed by a dynamic action provider, use
        ``/dynamic-action-provider/<provider>:<innerKind>/<innerName>`` (for
        example ``/dynamic-action-provider/my-mcp:tool/echo``).

        Args:
            key: The action key in the format ``/<kind>/<name>``.

        Returns:
            The ``Action`` instance if found, None otherwise.

        Raises:
            ValueError: If the key format is invalid or the kind is not a valid
                ``ActionKind``.
        """
        kind, name = parse_action_key(key)
        if kind == ActionKind.DYNAMIC_ACTION_PROVIDER:
            dap_parts = parse_dap_qualified_name(name)
            if dap_parts is not None:
                provider_action = await self.resolve_action(
                    ActionKind.DYNAMIC_ACTION_PROVIDER,
                    dap_parts.provider,
                )
                if provider_action is None:
                    return None
                dap = getattr(provider_action, GENKIT_DYNAMIC_ACTION_PROVIDER_ATTR, None)
                if dap is None:
                    return None
                try:
                    resolved = await dap.get_action(dap_parts.inner_kind, dap_parts.inner_name)
                except Exception as e:
                    logger.debug(
                        f'Dynamic action provider {dap_parts.provider} failed for '
                        f'qualified key {dap_parts.inner_kind}/{dap_parts.inner_name}',
                        exc_info=e,
                    )
                    return None
                if resolved is None:
                    return None
                return resolved
        return await self.resolve_action(kind, name)

    def register_schema(self, name: str, schema: dict[str, object], schema_type: type[BaseModel] | None = None) -> None:
        """Registers a schema by name.

        Schemas registered with this method can be referenced by name in
        .prompt files using the `output.schema` field.

        Args:
            name: The name of the schema.
            schema: The schema data (JSON schema format).
            schema_type: Optional Pydantic model class for runtime validation.

        Raises:
            ValueError: If a schema with the given name is already registered.
        """
        with self._lock:
            if name in self._schemas_by_name:
                raise ValueError(f'Schema "{name}" is already registered')
            self._schemas_by_name[name] = schema
            if schema_type is not None:
                self._schema_types_by_name[name] = schema_type
            logger.debug(f'Registered schema "{name}"')

    def lookup_schema(self, name: str) -> dict[str, object] | None:
        """Looks up a schema by name.

        Args:
            name: The name of the schema to look up.

        Returns:
            The schema data if found, None otherwise.  Falls back to parent.
        """
        with self._lock:
            local = self._schemas_by_name.get(name)
        if local is not None:
            return local
        return self._parent.lookup_schema(name) if self._parent is not None else None

    def lookup_schema_type(self, name: str) -> type[BaseModel] | None:
        """Looks up a schema's Pydantic type by name.

        Args:
            name: The name of the schema to look up.

        Returns:
            The Pydantic model class if found, None otherwise.  Falls back to parent.
        """
        with self._lock:
            local = self._schema_types_by_name.get(name)
        if local is not None:
            return local
        return self._parent.lookup_schema_type(name) if self._parent is not None else None

    # ===== Typed Action Lookups =====
    #
    # These methods provide type-safe access to actions of specific kinds.
    # They wrap resolve_action() with appropriate casts to preserve generic
    # type parameters that would otherwise be erased.

    async def resolve_embedder(self, name: str) -> Action[EmbedRequest, EmbedResponse, Never] | None:
        """Resolve an embedder action by name with full type information.

        Args:
            name: The embedder name (e.g., "my-embedder" or "plugin/embedder").

        Returns:
            A fully typed embedder action, or None if not found.
        """
        action = await self.resolve_action(ActionKind.EMBEDDER, name)
        if action is None:
            return None
        return cast(Action[EmbedRequest, EmbedResponse, Never], action)

    async def resolve_model(self, name: str) -> Action[ModelRequest, ModelResponse, ModelResponseChunk] | None:
        """Resolve a model action by name with full type information.

        Args:
            name: The model name (e.g., "gemini-pro" or "plugin/model").

        Returns:
            A fully typed model action, or None if not found.
        """
        action = await self.resolve_action(ActionKind.MODEL, name)
        if action is None:
            return None
        return cast(
            Action[ModelRequest, ModelResponse, ModelResponseChunk],
            action,
        )

    async def resolve_evaluator(self, name: str) -> Action[EvalRequest, EvalResponse, Never] | None:
        """Resolve an evaluator action by name with full type information.

        Args:
            name: The evaluator name (e.g., "my-evaluator" or "plugin/evaluator").

        Returns:
            A fully typed evaluator action, or None if not found.
        """
        action = await self.resolve_action(ActionKind.EVALUATOR, name)
        if action is None:
            return None
        return cast(Action[EvalRequest, EvalResponse, Never], action)
