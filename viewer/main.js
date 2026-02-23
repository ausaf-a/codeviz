import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRButton } from 'three/addons/webxr/VRButton.js';
import { XRControllerModelFactory } from 'three/addons/webxr/XRControllerModelFactory.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// Scene setup
const container = document.getElementById('container');
const loadingEl = document.getElementById('loading');
const infoEl = document.getElementById('info');

let camera, scene, renderer, controls;
let controller1, controller2;
let controllerGrip1, controllerGrip2;
let raycaster;
let spawnPoint = { x: 0, y: 1.6, z: 5 };

// Movement state
const moveState = {
    forward: false,
    backward: false,
    left: false,
    right: false,
    speed: 5,
};

// Clock for delta time
const clock = new THREE.Clock();

// Debug logging for Quest
function log(msg) {
    console.log('[CodeViz]', msg);
    // Also show on screen for Quest debugging
    const debugEl = document.getElementById('debug');
    if (debugEl) {
        debugEl.textContent += msg + '\n';
    }
}

init();
loadScene();

async function init() {
    log('Initializing...');

    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a12);
    scene.fog = new THREE.Fog(0x0a0a12, 50, 200);

    // Camera
    camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(spawnPoint.x, spawnPoint.y, spawnPoint.z);

    // Renderer - must set xr.enabled before adding VRButton
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.xr.enabled = true;
    container.appendChild(renderer.domElement);

    // Orbit controls for desktop
    controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(spawnPoint.x, spawnPoint.y - 0.5, spawnPoint.z - 5);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.update();

    // Lights
    const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 20, 10);
    scene.add(directionalLight);

    // Check WebXR support and add VR button
    await setupVR();

    // Raycaster for interaction
    raycaster = new THREE.Raycaster();

    // Event listeners
    window.addEventListener('resize', onWindowResize);
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('keyup', onKeyUp);

    // Start render loop
    renderer.setAnimationLoop(render);

    log('Initialization complete');
}

async function setupVR() {
    log('Setting up VR...');

    if (!('xr' in navigator)) {
        log('WebXR not available in navigator');
        showVRStatus('WebXR not supported');
        return;
    }

    try {
        const supported = await navigator.xr.isSessionSupported('immersive-vr');
        log(`immersive-vr supported: ${supported}`);

        if (supported) {
            // Add the official Three.js VR button
            const vrButton = VRButton.createButton(renderer);
            document.body.appendChild(vrButton);
            log('VR button added');
            showVRStatus('VR Ready - Click "Enter VR"');

            // Also set up controllers
            setupControllers();
        } else {
            showVRStatus('VR not supported on this device');
        }
    } catch (err) {
        log(`VR setup error: ${err.message}`);
        showVRStatus(`VR Error: ${err.message}`);
    }
}

function showVRStatus(msg) {
    const statusEl = document.getElementById('vr-status');
    if (statusEl) {
        statusEl.textContent = msg;
    }
}

function setupControllers() {
    const controllerModelFactory = new XRControllerModelFactory();

    controller1 = renderer.xr.getController(0);
    controller1.addEventListener('selectstart', onSelectStart);
    controller1.addEventListener('selectend', onSelectEnd);
    controller1.addEventListener('connected', (e) => log(`Controller 0 connected: ${e.data.handedness}`));
    scene.add(controller1);

    controllerGrip1 = renderer.xr.getControllerGrip(0);
    controllerGrip1.add(controllerModelFactory.createControllerModel(controllerGrip1));
    scene.add(controllerGrip1);

    controller2 = renderer.xr.getController(1);
    controller2.addEventListener('selectstart', onSelectStart);
    controller2.addEventListener('selectend', onSelectEnd);
    controller2.addEventListener('connected', (e) => log(`Controller 1 connected: ${e.data.handedness}`));
    scene.add(controller2);

    controllerGrip2 = renderer.xr.getControllerGrip(1);
    controllerGrip2.add(controllerModelFactory.createControllerModel(controllerGrip2));
    scene.add(controllerGrip2);

    // Controller ray visualization
    const lineGeometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(0, 0, -10)
    ]);
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0x4a9eff });

    controller1.add(new THREE.Line(lineGeometry.clone(), lineMaterial));
    controller2.add(new THREE.Line(lineGeometry.clone(), lineMaterial));

    // Listen for session start/end
    renderer.xr.addEventListener('sessionstart', () => {
        log('VR session started');
        showVRStatus('In VR');
    });
    renderer.xr.addEventListener('sessionend', () => {
        log('VR session ended');
        showVRStatus('VR Ready');
    });
}

async function loadScene() {
    const loader = new GLTFLoader();

    // Try to load spawn point
    try {
        const spawnResponse = await fetch('spawn.json');
        if (spawnResponse.ok) {
            const spawnData = await spawnResponse.json();
            if (spawnData.spawn_point) {
                spawnPoint.x = spawnData.spawn_point[0];
                spawnPoint.y = spawnData.spawn_point[1];
                spawnPoint.z = spawnData.spawn_point[2];
                camera.position.set(spawnPoint.x, spawnPoint.y, spawnPoint.z);
                controls.target.set(spawnPoint.x, spawnPoint.y - 0.5, spawnPoint.z + 5);
                controls.update();
                log(`Spawn point loaded: ${spawnPoint.x}, ${spawnPoint.y}, ${spawnPoint.z}`);
            }
        }
    } catch (e) {
        log('No spawn.json found, using default position');
    }

    // Load GLB scene
    loader.load(
        'scene.glb',
        (gltf) => {
            scene.add(gltf.scene);

            // Ensure materials are properly set up
            gltf.scene.traverse((child) => {
                if (child.isMesh) {
                    child.material.side = THREE.DoubleSide;
                    if (child.material.map) {
                        child.material.map.colorSpace = THREE.SRGBColorSpace;
                    }
                }
            });

            // Hide loading, show info
            loadingEl.classList.add('hidden');
            infoEl.classList.remove('hidden');

            log('Scene loaded successfully');
        },
        (progress) => {
            if (progress.total > 0) {
                const percent = (progress.loaded / progress.total * 100).toFixed(0);
                loadingEl.querySelector('p').textContent = `Loading Code Park... ${percent}%`;
            }
        },
        (error) => {
            log(`Error loading scene: ${error}`);
            loadingEl.querySelector('p').textContent = 'Error loading scene. Check console.';
            loadingEl.querySelector('.spinner').style.display = 'none';
        }
    );
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function onKeyDown(event) {
    switch (event.code) {
        case 'KeyW':
        case 'ArrowUp':
            moveState.forward = true;
            break;
        case 'KeyS':
        case 'ArrowDown':
            moveState.backward = true;
            break;
        case 'KeyA':
        case 'ArrowLeft':
            moveState.left = true;
            break;
        case 'KeyD':
        case 'ArrowRight':
            moveState.right = true;
            break;
    }
}

function onKeyUp(event) {
    switch (event.code) {
        case 'KeyW':
        case 'ArrowUp':
            moveState.forward = false;
            break;
        case 'KeyS':
        case 'ArrowDown':
            moveState.backward = false;
            break;
        case 'KeyA':
        case 'ArrowLeft':
            moveState.left = false;
            break;
        case 'KeyD':
        case 'ArrowRight':
            moveState.right = false;
            break;
    }
}

function onSelectStart(event) {
    const controller = event.target;
    controller.userData.isSelecting = true;
}

function onSelectEnd(event) {
    const controller = event.target;
    controller.userData.isSelecting = false;

    // Teleport on select end
    if (renderer.xr.isPresenting) {
        teleportOnRaycast(controller);
    }
}

function teleportOnRaycast(controller) {
    const tempMatrix = new THREE.Matrix4();
    tempMatrix.identity().extractRotation(controller.matrixWorld);

    raycaster.ray.origin.setFromMatrixPosition(controller.matrixWorld);
    raycaster.ray.direction.set(0, 0, -1).applyMatrix4(tempMatrix);

    const intersects = raycaster.intersectObjects(scene.children, true);

    for (const intersect of intersects) {
        // Check if we hit a floor/ground
        if (intersect.face && intersect.face.normal.y > 0.8) {
            const baseReferenceSpace = renderer.xr.getReferenceSpace();
            const offsetPosition = {
                x: -intersect.point.x,
                y: -intersect.point.y,
                z: -intersect.point.z,
                w: 1
            };
            const offsetRotation = new THREE.Quaternion();
            const transform = new XRRigidTransform(offsetPosition, offsetRotation);
            const teleportReferenceSpace = baseReferenceSpace.getOffsetReferenceSpace(transform);
            renderer.xr.setReferenceSpace(teleportReferenceSpace);
            break;
        }
    }
}

function handleVRMovement() {
    const session = renderer.xr.getSession();
    if (!session) return;

    for (const source of session.inputSources) {
        if (source.gamepad && source.handedness === 'left') {
            const axes = source.gamepad.axes;
            // Thumbstick movement
            if (Math.abs(axes[2]) > 0.1 || Math.abs(axes[3]) > 0.1) {
                const xrCamera = renderer.xr.getCamera();
                const direction = new THREE.Vector3();
                xrCamera.getWorldDirection(direction);
                direction.y = 0;
                direction.normalize();

                const right = new THREE.Vector3();
                right.crossVectors(direction, new THREE.Vector3(0, 1, 0));

                const movement = new THREE.Vector3();
                movement.addScaledVector(direction, -axes[3] * 0.05);
                movement.addScaledVector(right, axes[2] * 0.05);

                // Move the XR reference space
                const baseReferenceSpace = renderer.xr.getReferenceSpace();
                const offsetPosition = {
                    x: movement.x,
                    y: 0,
                    z: movement.z,
                    w: 1
                };
                const offsetRotation = new THREE.Quaternion();
                const transform = new XRRigidTransform(offsetPosition, offsetRotation);
                const newReferenceSpace = baseReferenceSpace.getOffsetReferenceSpace(transform);
                renderer.xr.setReferenceSpace(newReferenceSpace);
            }
        }
    }
}

function updateDesktopMovement(delta) {
    if (!renderer.xr.isPresenting) {
        const direction = new THREE.Vector3();
        camera.getWorldDirection(direction);
        direction.y = 0;
        direction.normalize();

        const right = new THREE.Vector3();
        right.crossVectors(direction, new THREE.Vector3(0, 1, 0));

        const velocity = moveState.speed * delta;

        if (moveState.forward) {
            camera.position.addScaledVector(direction, velocity);
            controls.target.addScaledVector(direction, velocity);
        }
        if (moveState.backward) {
            camera.position.addScaledVector(direction, -velocity);
            controls.target.addScaledVector(direction, -velocity);
        }
        if (moveState.left) {
            camera.position.addScaledVector(right, -velocity);
            controls.target.addScaledVector(right, -velocity);
        }
        if (moveState.right) {
            camera.position.addScaledVector(right, velocity);
            controls.target.addScaledVector(right, velocity);
        }
    }
}

function render() {
    const delta = clock.getDelta();

    // Update movement
    if (renderer.xr.isPresenting) {
        handleVRMovement();
    } else {
        updateDesktopMovement(delta);
        controls.update();
    }

    renderer.render(scene, camera);
}
