
export default defineEventHandler(async (event) => {
  const remote = process.env.VIZ_REMOTE || "http://viz.sif.svc.cluster.local:8080";
  let data = null
  try {
    return $fetch(`${remote}/api/sif`)
  } catch (err) {
    console.log(`Failed to carry request for ${remote}`)
    console.log(`The error is ${err}`)
  }
})
