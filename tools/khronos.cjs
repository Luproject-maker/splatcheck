// Adapter retains raw findings: unsupported extension warnings are not passes.
const fs = require('node:fs');
const validator = require('gltf-validator');
(async () => {
  const bytes = new Uint8Array(fs.readFileSync(process.argv[2]));
  const result = await validator.validateBytes(bytes, {maxIssues: 1000});
  process.stdout.write(JSON.stringify({version: validator.version(), issues: result.issues}));
})().catch(error => { process.stderr.write(String(error)); process.exitCode = 2; });
