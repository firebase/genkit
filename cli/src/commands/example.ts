// Example.

import { Command } from "commander";

interface ExampleOptions {
  uppercase?: boolean;
}

/** Example command. Registered in cli.ts */
export const example = new Command("example")
  .option("-u, --uppercase", "Uppercase the output", false)
  .action((options: ExampleOptions) => {
    const message = "this is an example command";
    if (options.uppercase) {
      console.log(message.toUpperCase());
    } else {
      console.log(message);
    }
  });
