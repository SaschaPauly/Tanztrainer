// Small process bridge lets Python's normative mutations exercise the JS reader.
const fs=require('node:fs');
const core=require('../src/choreo-core.js');
const schema=require('../shared/choreography.schema.json'),spec=require('../shared/validation-spec.json');
(async()=>{try{const result=await core.validate(new Blob([fs.readFileSync(process.argv[2])]),{schema,spec,limits:JSON.parse(process.argv[3]||'{}')});console.log(JSON.stringify({manifest:result.manifest}))}catch(error){console.log(JSON.stringify({error:error.message}))}})();
