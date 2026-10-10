import * as THREE from 'three'

// Shared by the original demo, real-building tools and Node regression tests.
export function checkVisibility(observerObject, observerConfig, target, obstacleObjects) {
  const origin = observerObject.position.clone()
  const toTarget = target.position.clone().sub(origin)
  const distance = toTarget.length()
  if (distance > observerConfig.maxDistance) return { visible: false, reason: '超出最大距离', distance }
  const targetDirection = toTarget.clone().normalize()
  const viewDirection = new THREE.Vector3(observerConfig.direction.x, observerConfig.direction.y, observerConfig.direction.z).normalize()
  const angle = THREE.MathUtils.radToDeg(viewDirection.angleTo(targetDirection))
  if (angle > observerConfig.fov / 2) return { visible: false, reason: '位于视野外', distance, angle }
  const hits = new THREE.Raycaster(origin, targetDirection, 0, distance).intersectObjects(obstacleObjects, false)
  if (hits.length) return { visible: false, reason: `被 ${hits[0].object.name} 遮挡`, distance, angle, blocker_id: hits[0].object.userData.id ?? null }
  return { visible: true, reason: '目标可见', distance, angle }
}
