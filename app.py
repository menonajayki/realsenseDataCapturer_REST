import os
from flask import Flask, jsonify, Response, request, render_template, send_file
from flask_restx import Api, Resource
from flask_swagger_ui import get_swaggerui_blueprint
import pyrealsense2 as rs
import numpy as np
import cv2
import datetime
import logging
import json

app = Flask(__name__, static_folder='static', template_folder='templates')
api = Api(app, version='1.0', title='RealSense Camera API', description='RealSense Camera API')

ns = api.namespace('camera', description='RealSense Camera Operations')

pipeline = None
config = None
camera_active = False

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# AAS Files
AAS_DIR = 'aas'

def initialize_camera():
    global pipeline, config, camera_active
    try:
        logger.debug("Initializing camera...")
        ctx = rs.context()
        devices = ctx.query_devices()
        logger.debug(f"Devices found: {len(devices)}")

        if len(devices) == 0:
            logger.debug("No RealSense devices connected.")
            return "No RealSense devices connected."

        if not camera_active:
            pipeline = rs.pipeline()
            config = rs.config()
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)  # Enable depth stream
            logger.debug("Starting pipeline...")
            pipeline.start(config)
            camera_active = True
            logger.debug("Camera started successfully.")
            return None
        else:
            logger.debug("Pipeline already initialized.")
            return None
    except rs.error as re:
        logger.error(f"RealSense error occurred: {re}")
        release_camera()
        return f"RealSense error occurred: {re}"
    except Exception as e:
        logger.error(f"Failed to start camera: {str(e)}")
        release_camera()
        return str(e)

def release_camera():
    global pipeline, camera_active
    if pipeline is not None:
        try:
            pipeline.stop()
            logger.debug("Pipeline stopped.")
        except Exception as e:
            logger.error(f"Failed to stop pipeline: {str(e)}")
        pipeline = None
    camera_active = False

@ns.route('/start')
class StartCamera(Resource):
    def post(self):
        error_message = initialize_camera()
        if camera_active:
            response = {
                "status": "Camera started",
                "timestamp": datetime.datetime.now().isoformat(),
                "publisher": "YourName"
            }
            logger.debug(f"Successful response: {response}")
            return jsonify(response)
        else:
            response = {
                "error": f"Failed to start camera: {error_message}",
                "timestamp": datetime.datetime.now().isoformat(),
                "publisher": "YourName"
            }
            logger.debug(f"Error response: {response}")
            return jsonify(response), 500

@ns.route('/stop')
class StopCamera(Resource):
    def post(self):
        release_camera()
        return jsonify({
            "status": "Camera stopped",
            "timestamp": datetime.datetime.now().isoformat(),
            "publisher": "YourName"
        })

@ns.route('/capture')
class CaptureImage(Resource):
    def get(self):
        if not camera_active:
            logger.debug("Camera is not active.")
            return jsonify({
                "error": "Camera is not active. Please start the camera before capturing images.",
                "timestamp": datetime.datetime.now().isoformat(),
                "publisher": "YourName"
            }), 400

        try:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()

            if not color_frame:
                logger.debug("No color frame captured.")
                return jsonify({
                    "error": "No color frame captured.",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "publisher": "YourName"
                }), 500

            color_image = np.asanyarray(color_frame.get_data())
            ret, jpeg = cv2.imencode('.jpg', color_image)
            if not ret:
                logger.debug("Failed to encode image to JPEG.")
                return jsonify({
                    "error": "Failed to encode image.",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "publisher": "YourName"
                }), 500

            return Response(jpeg.tobytes(), mimetype='image/jpeg')

        except Exception as e:
            logger.error(f"Exception occurred during image capture: {str(e)}")
            return jsonify({
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat(),
                "publisher": "YourName"
            }), 500

@ns.route('/capture3d')
class Capture3DImage(Resource):
    def get(self):
        if not camera_active:
            logger.debug("Camera is not active.")
            return jsonify({
                "error": "Camera is not active. Please start the camera before capturing images.",
                "timestamp": datetime.datetime.now().isoformat(),
                "publisher": "YourName"
            }), 400

        try:
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()

            if not depth_frame:
                logger.debug("No depth frame captured.")
                return jsonify({
                    "error": "No depth frame captured.",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "publisher": "YourName"
                }), 500

            depth_image = np.asanyarray(depth_frame.get_data())
            depth_image_normalized = cv2.normalize(depth_image, None, 0, 255, cv2.NORM_MINMAX)
            ret, jpeg = cv2.imencode('.jpg', depth_image_normalized)
            if not ret:
                logger.debug("Failed to encode 3D image to JPEG.")
                return jsonify({
                    "error": "Failed to encode 3D image.",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "publisher": "YourName"
                }), 500

            return Response(jpeg.tobytes(), mimetype='image/jpeg')

        except Exception as e:
            logger.error(f"Exception occurred during 3D image capture: {str(e)}")
            return jsonify({
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat(),
                "publisher": "YourName"
            }), 500

@ns.route('/status')
class CameraStatus(Resource):
    def get(self):
        status = {
            "camera_active": camera_active,
            "resolution": None,
            "frame_rate": None,
            "timestamp": datetime.datetime.now().isoformat(),
            "publisher": "YourName"
        }

        if camera_active:
            try:
                profile = pipeline.get_active_profile()
                video_stream = profile.get_stream(rs.stream.color).as_video_stream_profile()
                intrinsics = video_stream.get_intrinsics()
                frame_rate = video_stream.fps()
                status["resolution"] = f"{intrinsics.width}x{intrinsics.height}"
                status["frame_rate"] = frame_rate
            except Exception as e:
                status["error"] = str(e)
                logger.error(f"Status fetch error: {str(e)}")
        else:
            status["error"] = "Camera is not active"

        logger.debug(f"Status: {status}")
        return jsonify(status)

@ns.route('/settings')
class CameraSettings(Resource):
    def post(self):
        if not camera_active:
            return jsonify({
                "error": "Camera is not active. Please start the camera before updating settings.",
                "timestamp": datetime.datetime.now().isoformat(),
                "publisher": "YourName"
            }), 400

        try:
            width = int(request.json.get('width', 640))
            height = int(request.json.get('height', 480))
            frame_rate = int(request.json.get('frame_rate', 30))

            release_camera()

            global config
            config = rs.config()
            config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, frame_rate)
            config.enable_stream(rs.stream.depth, width, height, rs.format.z16, frame_rate)  # Enable depth stream
            pipeline = rs.pipeline()  # Recreate the pipeline
            pipeline.start(config)

            return jsonify({
                "status": "Settings updated",
                "timestamp": datetime.datetime.now().isoformat(),
                "publisher": "YourName"
            })

        except Exception as e:
            return jsonify({
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat(),
                "publisher": "YourName"
            }), 400


@app.route('/aas/ContactInformation', methods=['GET'])
def get_contact_information():
    try:
        file_path = os.path.join(AAS_DIR, 'ContactData.json')
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Failed to read ContactData.json: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/aas/SoftwareNamePlate', methods=['GET'])
def get_software_nameplate():
    try:
        file_path = os.path.join(AAS_DIR, 'SoftwareNamePlate.json')
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Failed to read SoftwareNamePlate.json: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Swagger
swagger_ui_blueprint = get_swaggerui_blueprint(
    '/swagger',
    '/static/swagger.json',
    config={
        'app_name': "RealSense Camera API"
    }
)
app.register_blueprint(swagger_ui_blueprint, url_prefix='/swagger')

@app.route('/view')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)  # Enable debug mode
    finally:
        release_camera()
