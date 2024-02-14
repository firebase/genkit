// TODO(sam-gc): Update this once we have actual libraries/plugins...

module.exports = {
  cliPlugins: [
    {keyword: 'tool-test', actions: [{name: 'hello', hook: () => console.log('Tool test!')}]}
  ]
}