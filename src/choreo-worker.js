'use strict';
importScripts('./choreo-core.js','./choreo-media.js');
onmessage=async({data})=>{
 try{
  const [schema,spec]=await Promise.all(['choreography.schema.json','validation-spec.json'].map(async name=>{
   const response=await fetch(new URL('../shared/'+name,self.location.href));if(!response.ok)throw Error('Formatvertrag konnte nicht geladen werden.');return response.json();
  }));
  const result=await ChoreoCore.validate(data.file,{schema,spec,onProgress:message=>postMessage({progress:message})});
  await ChoreoMedia.inspect(result.video,result.manifest);
  postMessage({result},[result.poses,result.timestamps]);
 }catch(error){postMessage({error:error.message||'Paket konnte nicht geprüft werden.'})}
};
