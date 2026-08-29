# app_camera.py
import streamlit as st
import cv2
import numpy as np
import time
import threading
import queue
import tempfile
import os

# Uses your module exactly as-is
from classification.classification_model import carregar_recursos, classificar_imagem

st.set_page_config(page_title="Real-Time Wound Classifier", page_icon="🩺", layout="centered")

# queues and constants
FRAME_QUEUE_MAXSIZE = 1
RESULT_QUEUE_MAXSIZE = 1

def probe_camera(index: int, timeout_sec: float = 1.0) -> bool:
    """Tries to open the camera at the given index and capture a quick frame. Returns True if OK."""
    cap = None
    try:
        cap = cv2.VideoCapture(index, cv2.CAP_ANY)
        if not cap.isOpened():
            return False
        # try reading a few frames
        t0 = time.time()
        while time.time() - t0 < timeout_sec:
            ret, _ = cap.read()
            if ret:
                return True
        return False
    except Exception:
        return False
    finally:
        try:
            if cap is not None:
                cap.release()
        except Exception:
            pass

def list_available_cameras(max_search: int = 6) -> list[int]:
    """Searches for cameras at indices 0..(max_search-1). Returns the list of available indices."""
    available = []
    for i in range(max_search):
        if probe_camera(i, timeout_sec=0.6):
            available.append(i)
    return available

def camera_capture_loop(frame_q: queue.Queue, stop_event: threading.Event, device_index: int = 0, width:int=640, height:int=480):
    """Captures frames from the camera and puts them in the queue (BGR). Keeps only the most recent frame."""
    cap = cv2.VideoCapture(device_index, cv2.CAP_ANY)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    if not cap.isOpened():
        print(f"ERROR: could not open camera {device_index}.")
        stop_event.set()
        return

    try:
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            # keep only the latest frame
            try:
                if frame_q.full():
                    _ = frame_q.get_nowait()
                frame_q.put_nowait(frame)
            except Exception:
                pass

            # small pause to ease CPU load
            time.sleep(0.01)
    finally:
        cap.release()

def processing_loop(frame_q: queue.Queue, result_q: queue.Queue, stop_event: threading.Event):
    """Pulls frames from the queue, saves a temp file, calls classificar_imagem(path) and puts the result in the queue."""
    while not stop_event.is_set():
        try:
            frame = frame_q.get(timeout=0.5)
        except queue.Empty:
            continue

        try:
            # Save the frame to a temporary file (needed because your function takes a path)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
            # cv2.imwrite expects BGR; the frame is already in BGR
            cv2.imwrite(tmp_path, frame)

            # Call your model's function
            result = classificar_imagem(tmp_path)

            # Remove the temporary file
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        except Exception as e:
            result = {"status": "erro", "mensagem": str(e)}

        # Keep only the latest result
        try:
            if result_q.full():
                _ = result_q.get_nowait()
            result_q.put_nowait((frame, result))
        except Exception:
            pass

        # small pause
        time.sleep(0.01)

def start_camera_threads(cam_state: dict, device_index: int):
    """Helper to safely start threads."""
    cam_state['frame_q'] = queue.Queue(maxsize=FRAME_QUEUE_MAXSIZE)
    cam_state['result_q'] = queue.Queue(maxsize=RESULT_QUEUE_MAXSIZE)
    cam_state['stop_event'] = threading.Event()

    cam_state['capture_thread'] = threading.Thread(
        target=camera_capture_loop,
        args=(cam_state['frame_q'], cam_state['stop_event'], device_index),
        daemon=True
    )
    cam_state['process_thread'] = threading.Thread(
        target=processing_loop,
        args=(cam_state['frame_q'], cam_state['result_q'], cam_state['stop_event']),
        daemon=True
    )
    cam_state['capture_thread'].start()
    cam_state['process_thread'].start()
    cam_state['device_index'] = device_index

def stop_camera_threads(cam_state: dict):
    """Helper to safely stop threads."""
    try:
        if cam_state.get('stop_event'):
            cam_state['stop_event'].set()
        if cam_state.get('capture_thread'):
            cam_state['capture_thread'].join(timeout=1.0)
        if cam_state.get('process_thread'):
            cam_state['process_thread'].join(timeout=1.0)
    except Exception:
        pass
    finally:
        cam_state['capture_thread'] = None
        cam_state['process_thread'] = None
        cam_state['frame_q'] = None
        cam_state['result_q'] = None
        cam_state['stop_event'] = None
        cam_state['device_index'] = None

def main():
    st.title("🔬 Real-Time Wound Classifier (OpenCV)")
    st.markdown("Run locally (`python -m streamlit run app_camera.py`). The camera needs to be accessible to the server (your computer).")

    # Load the model once (blocking) before starting threads
    if 'modelo_carregado' not in st.session_state:
        with st.spinner("Loading model... (this may take a while)"):
            st.session_state.modelo_carregado = carregar_recursos()
        if st.session_state.modelo_carregado:
            st.success("✅ Model loaded!")
        else:
            st.error("❌ Failed to load model, check the path/files.")
            return

    # Camera detection/selection panel
    st.sidebar.header("Cameras")
    max_probe = st.sidebar.number_input("Search indices 0..N-1 (N)", min_value=1, max_value=16, value=6, step=1)
    if 'available_cameras' not in st.session_state:
        st.session_state.available_cameras = []

    if st.sidebar.button("🔎 Detect cameras"):
        with st.spinner("Detecting cameras..."):
            st.session_state.available_cameras = list_available_cameras(max_search=int(max_probe))
        st.sidebar.success(f"Found: {len(st.session_state.available_cameras)}")

    # Show detection results and allow selection
    cam_options = [f"{i} - Camera {i}" for i in st.session_state.available_cameras]
    cam_options.insert(0, "manual: type index")

    selected_option = st.sidebar.selectbox("Select an available camera", cam_options, index=0)
    if selected_option.startswith("manual"):
        selected_index = st.sidebar.number_input("Manual camera index", min_value=0, max_value=31, value=0, step=1)
    else:
        selected_index = int(selected_option.split(" - ")[0])

    # Main controls
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        fps = st.slider("Target FPS (UI)", 1, 10, 2)
    with col2:
        start = st.checkbox("🔴 Start/Stop camera", value=False, key="start_camera")
    with col3:
        refresh_detect = st.button("🔁 Re-detect")

    # Allow manual redetect button
    if refresh_detect:
        with st.sidebar.spinner("Re-detecting..."):
            st.session_state.available_cameras = list_available_cameras(max_search=int(max_probe))
        st.sidebar.success(f"Found: {len(st.session_state.available_cameras)}")

    # Placeholders
    image_placeholder = st.empty()
    info_placeholder = st.empty()

    # session_state for threads/queues
    if 'cam_state' not in st.session_state:
        st.session_state.cam_state = {
            'frame_q': None,
            'result_q': None,
            'stop_event': None,
            'capture_thread': None,
            'process_thread': None,
            'device_index': None,
        }

    cam = st.session_state.cam_state

    # Start/Stop / Switch camera logic
    if start:
        # if not started, or device changed, start threads with selected_index
        need_start = False
        if cam['capture_thread'] is None or not cam['capture_thread'].is_alive():
            need_start = True
        elif cam.get('device_index') is not None and cam['device_index'] != selected_index:
            # switch device: stop and restart
            stop_camera_threads(cam)
            need_start = True

        if need_start:
            try:
                start_camera_threads(cam, selected_index)
                st.success(f"Camera started (device {selected_index}).")
            except Exception as e:
                st.error(f"Failed to start camera {selected_index}: {e}")
                stop_camera_threads(cam)
    else:
        # stop if running
        if cam['capture_thread'] is not None:
            stop_camera_threads(cam)
            st.info("Camera stopped.")

    # Main UI loop: updates to show the latest frame/result
    try:
        while start:
            frame = None
            result = None

            # try to get the latest result (frame + result)
            try:
                frame, result = cam['result_q'].get_nowait()
            except Exception:
                # if there's no result, try to get just the raw frame
                try:
                    frame = cam['frame_q'].get_nowait()
                except Exception:
                    frame = None

            if frame is not None:
                display = frame.copy()
                if result and result.get('status') == 'sucesso':
                    h, w = display.shape[:2]
                    cv2.rectangle(display, (30, 30), (w-30, h-30), (0, 0, 255), 2)
                    texto = f"{result['classe_traduzida']} ({result['confianca_predita_percentual']})"
                    cv2.putText(display, texto, (40, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,255), 2)
                    info_placeholder.success(f"Prediction: {result['classe_traduzida']} | Confidence: {result['confianca_predita_percentual']}")
                elif result and result.get('status') == 'erro':
                    cv2.putText(display, f"ERROR: {result.get('mensagem')}", (40, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                    info_placeholder.error(f"Error: {result.get('mensagem')}")
                else:
                    info_placeholder.info("Waiting for prediction...")

                # convert BGR->RGB and display
                display_rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
                image_placeholder.image(display_rgb, width='content')
            else:
                image_placeholder.text("Waiting for camera frame...")
                info_placeholder.text("...")

            # control the UI refresh rate
            time.sleep(1.0 / max(1, fps))

            # if the user unchecked the checkbox externally, exit the loop
            if not st.session_state.get("start_camera", False):
                break

    except Exception as e:
        st.error(f"UI error: {e}")

    # final cleanup (make sure threads stop if the app is closed)
    if cam.get('stop_event') and not cam['stop_event'].is_set():
        cam['stop_event'].set()

if __name__ == "__main__":
    main()
