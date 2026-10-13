// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

//go:build unix && !linux

package exp

import "syscall"

// setParentDeathSignal is a no-op where the kernel has no parent-death
// signal; the box notices its host is gone through the dropped socket, and
// child runtimes clean up their own boxes on exit (see trackChild).
func setParentDeathSignal(*syscall.SysProcAttr) {}
