# Copyright 2026 Google LLC
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

class Releasekit < Formula
  include Language::Python::Virtualenv

  desc "Release orchestration for polyglot monorepos"
  homepage "https://github.com/firebase/genkit"
  url "https://files.pythonhosted.org/packages/source/r/releasekit/releasekit-0.1.0.tar.gz"
  sha256 "PLACEHOLDER"
  license "Apache-2.0"

  depends_on "python@3.13"

  resource "aiofiles" do
    url "https://files.pythonhosted.org/packages/source/a/aiofiles/aiofiles-24.1.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "argcomplete" do
    url "https://files.pythonhosted.org/packages/source/a/argcomplete/argcomplete-3.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "diagnostic" do
    url "https://files.pythonhosted.org/packages/source/d/diagnostic/diagnostic-3.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/source/h/httpx/httpx-0.27.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "jinja2" do
    url "https://files.pythonhosted.org/packages/source/j/jinja2/jinja2-3.1.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "packaging" do
    url "https://files.pythonhosted.org/packages/source/p/packaging/packaging-24.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "rich-argparse" do
    url "https://files.pythonhosted.org/packages/source/r/rich-argparse/rich_argparse-1.6.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "structlog" do
    url "https://files.pythonhosted.org/packages/source/s/structlog/structlog-25.1.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "tomlkit" do
    url "https://files.pythonhosted.org/packages/source/t/tomlkit/tomlkit-0.13.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/releasekit --version")
  end
end
