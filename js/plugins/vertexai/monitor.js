const { exec } = require('child_process');

// Log initial memory usage
console.log('Initial Memory Usage:', process.memoryUsage());

const buildProcess = exec('pnpm run build', (error, stdout, stderr) => {
  if (error) {
    console.error(`Error during build: ${error.message}`);
    return;
  }
  console.log(`Build output: ${stdout}`);
  console.error(`Build errors: ${stderr}`);
});

// Monitor memory usage at intervals
const interval = setInterval(() => {
  console.log('Memory Usage during Build:', process.memoryUsage());
}, 5000);

buildProcess.on('exit', (code) => {
  clearInterval(interval);
  console.log(`Build process exited with code ${code}`);
  console.log('Final Memory Usage:', process.memoryUsage());
});
