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

"""Resource module for defining and managing resources.

Resources in Genkit represent addressable content or data processing units containing
unstructured data (Post, PDF, etc.) that can be retrieved or generated. They are
identified by URIs (e.g. `file://`, `http://`, `gs://`) and can be static (fixed URI)
or dynamic (using URI templates).

This module provides tools to define resource actions that can resolve these URIs
and return content (`ResourceOutput`) containing `Part`s.
"""

import re
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypedDict

from pydantic import BaseModel

from genkit.core.action import Action, ActionRunContext
from genkit.core.action.types import ActionKind
from genkit.core.registry import Registry
from genkit.core.typing import Metadata, Part


class ResourceOptions(TypedDict, total=False):
    """Options for defining a resource.

    Attributes:
        name: Resource name. If not specified, uri or template will be used as name.
        uri: The URI of the resource. Can contain template variables for simple matches,
             but `template` is preferred for pattern matching.
        template: The URI template (ex. `my://resource/{id}`). See RFC6570 for specification.
                  Used for matching variable resources.
        description: A description of the resource, used for documentation and discovery.
        metadata: Arbitrary metadata to attach to the resource action.
    """

    name: str
    uri: str
    template: str
    description: str
    metadata: dict[str, Any]


class ResourceInput(BaseModel):
    """Input structure for a resource request.

    Attributes:
        uri: The full URI being requested/resolved.
    """

    uri: str


class ResourceOutput(BaseModel):
    """Output structure from a resource resolution.

    Attributes:
        content: A list of `Part` objects representing the resource content.
    """

    content: list[Part]


class ResourceFn(Protocol):
    """A function that returns parts for a given resource.

    The function receives the resolved input (including the URI) and context,
    and should return a `ResourceOutput` containing the content parts.
    """

    def __call__(self, input: ResourceInput, ctx: ActionRunContext) -> Awaitable[ResourceOutput]: ...


ResourceArgument = Action | str


async def resolve_resources(registry: Registry, resources: list[ResourceArgument] | None = None) -> list[Action]:
    """Resolves a list of resource names or actions into a list of Action objects.

    Args:
        registry: The registry to lookup resources in.
        resources: A list of resource references, which can be either direct `Action`
                   objects or strings (names/URIs).

    Returns:
        A list of resolved `Action` objects.

    Raises:
        ValueError: If a resource reference is invalid or cannot be found.
    """
    if not resources:
        return []

    resolved_actions = []
    for ref in resources:
        if isinstance(ref, str):
            resolved_actions.append(await lookup_resource_by_name(registry, ref))
        elif isinstance(ref, Action):
            resolved_actions.append(ref)
        else:
            raise ValueError('Resources must be strings or actions')
    return resolved_actions


async def lookup_resource_by_name(registry: Registry, name: str) -> Action:
    """Looks up a resource action by name in the registry.

    Tries to resolve the name directly, or with common prefixes like `/resource/`
    or `/dynamic-action-provider/`.

    Args:
        registry: The registry to search.
        name: The name or URI of the resource to lookup.

    Returns:
        The found `Action`.

    Raises:
        ValueError: If the resource cannot be found.
    """
    resource = (
        registry.lookup_action(ActionKind.RESOURCE, name)
        or registry.lookup_action(ActionKind.RESOURCE, f'/resource/{name}')
        or registry.lookup_action(ActionKind.RESOURCE, f'/dynamic-action-provider/{name}')
    )
    if not resource:
        raise ValueError(f'Resource {name} not found')
    return resource


def define_resource(registry: Registry, opts: ResourceOptions, fn: ResourceFn) -> Action:
    """Defines a resource and registers it with the given registry.

    This creates a resource action that can handle requests for a specific URI
    or URI template.

    Args:
        registry: The registry to register the resource with.
        opts: Options defining the resource (name, uri, template, etc.).
        fn: The function that implements resource content retrieval.

    Returns:
        The registered `Action` for the resource.
    """
    action = dynamic_resource(opts, fn)

    action.matches = create_matcher(opts.get('uri'), opts.get('template'))

    # Mark as not dynamic since it's being registered
    action.metadata['dynamic'] = False

    registry.register_action_from_instance(action)

    # We need to return the registered action from the registry if we want it to be the exact same instance
    # but the one created by dynamic_resource is fine too if it has the same properties.
    return action


def resource(opts: ResourceOptions, fn: ResourceFn) -> Action:
    """Defines a dynamic resource action without immediate registration.

    This is an alias for `dynamic_resource`. Useful for defining resources that
    might be registered later or used as standalone actions.

    Args:
        opts: Options defining the resource.
        fn: The resource implementation function.

    Returns:
        The created `Action`.
    """
    return dynamic_resource(opts, fn)


def dynamic_resource(opts: ResourceOptions, fn: ResourceFn) -> Action:
    """Defines a dynamic resource action.

    Creates an `Action` of kind `RESOURCE` that wraps the provided function.
    The wrapper handles:
    1. Input validation and matching against the URI/Template.
    2. Execution of the resource function.
    3. Post-processing of output to attach metadata (like parent resource info).

    Args:
        opts: Options including `uri` or `template` for matching.
        fn: The function performing the resource retrieval.

    Returns:
        An `Action` configured as a resource.

    Raises:
        ValueError: If neither `uri` nor `template` is provided in options.
    """
    uri = opts.get('uri') or opts.get('template')
    if not uri:
        raise ValueError('must specify either uri or template options')

    matcher = create_matcher(opts.get('uri'), opts.get('template'))

    async def wrapped_fn(input_data: ResourceInput, ctx: ActionRunContext) -> ResourceOutput:
        if isinstance(input_data, dict):
            input_data = ResourceInput(**input_data)

        try:
            template_match = matcher(input_data)
            if not template_match:
                raise ValueError(f'input {input_data} did not match template {uri}')

            parts = await fn(input_data, ctx)

            # Post-processing parts to add metadata
            content_list = parts.content if hasattr(parts, 'content') else parts.get('content', [])

            for p in content_list:
                if isinstance(p, Part):
                    p = p.root

                if hasattr(p, 'metadata'):
                    if p.metadata is None:
                        p.metadata = {}

                    if isinstance(p.metadata, Metadata):
                        p_metadata = p.metadata.root
                    else:
                        p_metadata = p.metadata

                    if 'resource' in p_metadata:
                        if 'parent' not in p_metadata['resource']:
                            p_metadata['resource']['parent'] = {'uri': input_data.uri}
                            if opts.get('template'):
                                p_metadata['resource']['parent']['template'] = opts.get('template')
                    else:
                        p_metadata['resource'] = {'uri': input_data.uri}
                        if opts.get('template'):
                            p_metadata['resource']['template'] = opts.get('template')
                elif isinstance(p, dict):
                    if 'metadata' not in p or p['metadata'] is None:
                        p['metadata'] = {}
                    p_metadata = p['metadata']
                else:
                    continue
            # Ensure we return a serializable dict (handling Pydantic models in list)
            if isinstance(parts, BaseModel):
                return parts.model_dump()
            elif isinstance(parts, dict):
                # Verify content items are dicts, if not dump them
                if 'content' in parts:
                    parts['content'] = [p.model_dump() if isinstance(p, BaseModel) else p for p in parts['content']]
                return parts
            return parts
        except Exception as e:
            raise e

            # Since p.metadata is a dict in Pydantic RootModel for Metadata usually, assuming it's accessible.
            # Part -> ResourcePart | etc. ResourcePart has resource: Resource1.
            # But the JS code puts it in metadata.resource.
            # In Python typing.py, Metadata is RootModel[dict[str, Any]].

            if 'resource' in p_metadata:
                if 'parent' not in p_metadata['resource']:
                    p_metadata['resource']['parent'] = {'uri': input_data.uri}
                    if opts.get('template'):
                        p_metadata['resource']['parent']['template'] = opts.get('template')
            else:
                p_metadata['resource'] = {'uri': input_data.uri}
                if opts.get('template'):
                    p_metadata['resource']['template'] = opts.get('template')

        return parts

    name = opts.get('name') or uri

    act = Action(
        kind=ActionKind.RESOURCE,
        name=name,
        fn=wrapped_fn,
        description=opts.get('description'),
        # input_schema=ResourceInput,
        # Action expects schema? Action definition has metadata_fn usually
        metadata={
            'resource': {
                'uri': opts.get('uri'),
                'template': opts.get('template'),
            },
            **(opts.get('metadata') or {}),
            'type': 'resource',
            'dynamic': True,
        },
    )

    act.matches = matcher
    return act


def create_matcher(uri_opt: str | None, template_opt: str | None) -> Callable[[ResourceInput], bool]:
    """Creates a matching function for resource inputs.

    Args:
        uri_opt: An exact URI string to match.
        template_opt: A URI template string to match (e.g. `file://{path}`).

    Returns:
        A callable that takes `ResourceInput` and returns `True` if it matches,
        `False` otherwise.
    """
    # TODO: normalize resource URI
    if uri_opt:
        return lambda input: input.uri == uri_opt

    if template_opt:
        # Improved regex matching to support basic RFC 6570 patterns.
        #
        # Why not use uritemplate library?
        # The python-hyper/uritemplate library matches the RFC 6570 spec well for *expansion*
        # (Template + Vars -> URI), but it does not support "reverse matching" or parsing
        # (URI -> Vars) which is required here to match an incoming URI against a template.
        #
        # To patch uritemplate to support this, we would need to:
        # 1. Expose the parsed template tokens (literals and expressions).
        # 2. Implement a compiler that converts these tokens into a regular expression,
        #    mapping expression types (e.g. {var}, {+var}) to appropriate regex groups.
        #    - Simple string expansion {var}: ([^/]+) - stops at reserved characters.
        #    - Reserved expansion {+var}: (.+) - matches reserved characters like slashes.
        #
        # Until then, we use a lightweight regex implementation that covers the most common
        # use cases in Genkit resources.

        # escaping the template string
        pattern_str = re.escape(template_opt)
        
        # Handle reserved expansion {+var} -> (.+) (matches everything including slashes)
        pattern_str = re.sub(r'\\\{\\\+[^}]+\\\}', '(.+)', pattern_str)
        
        # Handle simple expansion {var} -> ([^/]+) (matches path segment)
        pattern_str = re.sub(r'\\\{[^}]+\\\}', '([^/]+)', pattern_str)
        
        # Ensure full match
        pattern = re.compile(f'^{pattern_str}$')

        return lambda input: pattern.match(input.uri) is not None

    return lambda input: False


async def find_matching_resource(
    registry: Registry, resources: list[Action], input_data: ResourceInput
) -> Action | None:
    """Finds a registered or provided resource action that matches the input.

    Searches through the provided `resources` list (first priority) and then
    the global registry for any resource action that matches the `input_data.uri`.

    Args:
        registry: The registry to search.
        resources: A list of explicitly provided actions to check first.
        input_data: The input containing the URI to match.

    Returns:
        The matching `Action` if found, `None` otherwise.
    """
    # First look in any resources explicitly listed
    for res in resources:
        if hasattr(res, 'matches') and res.matches(input_data):
            return res

    # Then search the registry
    # In python registry.list_actions returns dict[str, Action] or we can use lookup logic.
    # Registry doesn't expose easy iteration over all actions by key pattern directly efficienty except list_actions.

    # We need list_actions but current registry.list_actions expects us to pass a dict to fill?
    # Or list_serializable_actions returns dict.

    # We can access _entries but that's private.
    # We should add a method to Registry if needed, or use public API.
    # registry.list_actions() exists.

    all_actions = registry.list_serializable_actions({ActionKind.RESOURCE})
    if not all_actions:
        return None

    for key in all_actions:
        action = registry.lookup_action_by_key(key)
        if action and hasattr(action, 'matches') and action.matches(input_data):
            return action

    return None


def is_dynamic_resource_action(obj: Any) -> bool:
    """Checks if an object is a dynamic resource action.

    Dynamic resources are actions that haven't been registered yet or are explicitly
    marked as dynamic (often matching multiple URIs via template).

    Args:
        obj: The object to check.

    Returns:
        True if the object is an Action of kind RESOURCE and marked dynamic.
    """
    return isinstance(obj, Action) and obj.metadata.get('dynamic') is True
