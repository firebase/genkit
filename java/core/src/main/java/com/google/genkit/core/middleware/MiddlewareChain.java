/*
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

package com.google.genkit.core.middleware;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.function.BiFunction;

import com.google.genkit.core.ActionContext;
import com.google.genkit.core.GenkitException;

/**
 * MiddlewareChain manages a list of middleware and provides execution of the
 * complete chain. It implements the chain of responsibility pattern where each
 * middleware can process or modify the request/response.
 *
 * @param <I>
 *            The input type
 * @param <O>
 *            The output type
 */
public class MiddlewareChain<I, O> {

  private final List<Middleware<I, O>> middlewareList;

  /**
   * Creates a new MiddlewareChain.
   */
  public MiddlewareChain() {
    this.middlewareList = new ArrayList<>();
  }

  /**
   * Creates a new MiddlewareChain with the given middleware.
   *
   * @param middlewareList
   *            the initial list of middleware
   */
  public MiddlewareChain(List<Middleware<I, O>> middlewareList) {
    this.middlewareList = new ArrayList<>(middlewareList);
  }

  /**
   * Creates a copy of this MiddlewareChain.
   *
   * @return a new MiddlewareChain with the same middleware
   */
  public MiddlewareChain<I, O> copy() {
    return new MiddlewareChain<>(this.middlewareList);
  }

  /**
   * Adds a middleware to the chain.
   *
   * @param middleware
   *            the middleware to add
   * @return this chain for fluent chaining
   */
  public MiddlewareChain<I, O> use(Middleware<I, O> middleware) {
    if (middleware != null) {
      middlewareList.add(middleware);
    }
    return this;
  }

  /**
   * Adds multiple middleware to the chain.
   *
   * @param middlewareList
   *            the middleware to add
   * @return this chain for fluent chaining
   */
  public MiddlewareChain<I, O> useAll(List<Middleware<I, O>> middlewareList) {
    if (middlewareList != null) {
      this.middlewareList.addAll(middlewareList);
    }
    return this;
  }

  /**
   * Inserts a middleware at the beginning of the chain.
   *
   * @param middleware
   *            the middleware to insert
   * @return this chain for fluent chaining
   */
  public MiddlewareChain<I, O> useFirst(Middleware<I, O> middleware) {
    if (middleware != null) {
      middlewareList.add(0, middleware);
    }
    return this;
  }

  /**
   * Returns an unmodifiable view of the middleware list.
   *
   * @return the middleware list
   */
  public List<Middleware<I, O>> getMiddlewareList() {
    return Collections.unmodifiableList(middlewareList);
  }

  /**
   * Returns the number of middleware in the chain.
   *
   * @return the middleware count
   */
  public int size() {
    return middlewareList.size();
  }

  /**
   * Checks if the chain is empty.
   *
   * @return true if no middleware is registered
   */
  public boolean isEmpty() {
    return middlewareList.isEmpty();
  }

  /**
   * Clears all middleware from the chain.
   */
  public void clear() {
    middlewareList.clear();
  }

  /**
   * Executes the middleware chain with the given request, context, and final
   * action.
   *
   * @param request
   *            the input request
   * @param context
   *            the action context
   * @param finalAction
   *            the final action to execute after all middleware
   * @return the output response
   * @throws GenkitException
   *             if execution fails
   */
  public O execute(I request, ActionContext context, BiFunction<ActionContext, I, O> finalAction)
      throws GenkitException {
    return dispatch(0, request, context, finalAction);
  }

  /**
   * Dispatches to the next middleware in the chain or the final action.
   *
   * @param index
   *            the current middleware index
   * @param request
   *            the input request
   * @param context
   *            the action context
   * @param finalAction
   *            the final action to execute
   * @return the output response
   * @throws GenkitException
   *             if execution fails
   */
  private O dispatch(int index, I request, ActionContext context, BiFunction<ActionContext, I, O> finalAction)
      throws GenkitException {
    if (index >= middlewareList.size()) {
      // End of middleware chain, execute the final action
      return finalAction.apply(context, request);
    }

    Middleware<I, O> currentMiddleware = middlewareList.get(index);

    // Create the next function that will dispatch to the next middleware
    MiddlewareNext<I, O> next = (modifiedRequest, modifiedContext) -> dispatch(index + 1,
        modifiedRequest != null ? modifiedRequest : request,
        modifiedContext != null ? modifiedContext : context, finalAction);

    return currentMiddleware.handle(request, context, next);
  }

  /**
   * Creates a new MiddlewareChain with the specified middleware.
   *
   * @param middleware
   *            the middleware to include
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a new MiddlewareChain
   */
  @SafeVarargs
  public static <I, O> MiddlewareChain<I, O> of(Middleware<I, O>... middleware) {
    MiddlewareChain<I, O> chain = new MiddlewareChain<>();
    for (Middleware<I, O> m : middleware) {
      chain.use(m);
    }
    return chain;
  }
}
