// Fixed local worker: shares the browser's geometry implementation, no network/model.
import { buildingMeshes, executeInspectionTool } from '../src/inspection-core.js'
let input = ''
for await (const chunk of process.stdin) input += chunk
try {
  const { data, name, args, schemes } = JSON.parse(input)
  process.stdout.write(JSON.stringify(executeInspectionTool(name,args,data,buildingMeshes(data),schemes)))
} catch (error) {
  process.stderr.write(error.message)
  process.exitCode = 1
}
