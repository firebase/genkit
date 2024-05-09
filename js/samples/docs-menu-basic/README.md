# Copyright 2024 Google LLC

#

# Licensed under the Apache License, Version 2.0 (the "License");

# you may not use this file except in compliance with the License.

# You may obtain a copy of the License at

#

# http://www.apache.org/licenses/LICENSE-2.0

#

# Unless required by applicable law or agreed to in writing, software

# distributed under the License is distributed on an "AS IS" BASIS,

# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

# See the License for the specific language governing permissions and

# limitations under the License.

# Evaluating menuQA flow

## Build it

```
pnpm build
```

or if you need to, build everything:

```
cd </path/to/genkit>; pnpm build; pnpm pack:all; cd -
```

where `</path/to/genkit>` is the top level of the genkit repo

## Run the flow via cli

```
genkit flow:run menuSuggestionFlow '"astronauts"'
```

## Run the flow in the Developer UI

```
genkit start
```

Click on menuSuggestionFlow in the lefthand navigation panel to playground the new flow.
