from http.server import HTTPServer, BaseHTTPRequestHandler
import os, json, sys
import requests
import time
from datetime import datetime
from http import HTTPStatus
from multiprocessing import Process, Pipe, TimeoutError

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

#from data_processing.create_dataset import dataset_out_of_hmi_data
#from src.train import Siamese_train
#from inference import Inference
#from config_src import (
#    EPOCHS, LEARNING_RATE, WEIGHT_DECAY, DATA_ROOT_DIR,
#    IO_DIR, NIO_DIR, MODEL_LOAD_PATH, VALID_SPLIT, DATASET_MEAN, DATASET_STD, DROP_RATE, STORE_CSV)
from server_port_ip import (
    BACKEND_IP, BACKEND_PORT, HMI_SERVER)


requests.packages.urllib3.disable_warnings()

EMULATE_TRAINING = True
EMULATE_INFERENCE = True
BACKEND_SRV = 'http://' + BACKEND_IP + ':' + str(BACKEND_PORT) +'/'
STATUS_FILE = currentdir + '/srv_files/srv_dicts.json'



# Read current configuration/status file
f = open(STATUS_FILE) 
general_dict = json.load(f)
status_dict = general_dict['general_status']
available_states = {available_state: index for index, available_state in enumerate(status_dict['available_states'])}
status_dict['current_state'] = available_states['idle']
train_dict = general_dict['state_train']
inference_dict = general_dict['state_inference']
error_dict = general_dict['state_error']
f.close()

# Global threads
InfThread = None
TrainThread = None

# Pipe for multi-process communication
parent_conn, child_conn = Pipe()

class Serv(BaseHTTPRequestHandler):
    
    # Expand parent's init method
    def __init__(self, *args, **kwargs):
        self.msg = {}
        
        super().__init__(*args, **kwargs)

    def do_GET(self):
        # Tell the Python interpreter which are global variables
        global InfThread, TrainThread, parent_conn, child_conn, status_dict, train_dict, general_dict, inference_dict, error_dict
        
        if self.path == '/help':
            self.path = currentdir + '/srv_files/help.html'
            try:
                file_to_open = open(self.path).read()
                file_bin = bytes(file_to_open, 'utf-8')
                self.send_response(HTTPStatus.OK)
            except:
                file_to_open = "File not found"
                self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header("Content-type", "text/html")
            self.send_header("Content-Length", len(file_bin))
            self.end_headers()
            self.wfile.write(file_bin)
            
        elif self.path == '/dbg_srv':
            self.path = currentdir + '/serv.py'
            try:
                file_to_open = open(self.path).read()
                file_bin = bytes(file_to_open, 'utf-8')
                self.send_response(HTTPStatus.OK)
            except:
                file_to_open = "File not found"
                self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header("Content-type", "text/plain")
            self.send_header("Content-Length", len(file_bin))
            self.end_headers()
            self.wfile.write(file_bin)
            
        elif self.path == '/dbg_conf':
            self.path = currentdir + '/srv_files/srv_dicts.json'
            try:
                file_to_open = open(self.path).read()
                file_bin = bytes(file_to_open, 'utf-8')
                self.send_response(HTTPStatus.OK)
            except:
                file_to_open = "File not found"
                self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header("Content-type", "text/json")
            self.send_header("Content-Length", len(file_bin))
            self.end_headers()
            self.wfile.write(file_bin)
        
        elif self.path == '/getstatus':
            bin_dict = json.dumps(status_dict).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-Length", len(bin_dict))
            self.end_headers()
            self.wfile.write(bin_dict)
            
        elif '/startTraining' in self.path or '/starttraining' in self.path:
            # Parse Params
            i = self.path.index ( "?" ) + 1
            params = dict ( [ tuple ( p.split("=") ) for p in self.path[i:].split ( "&" ) ] )
                
            # Check call from right state
            if status_dict['current_state'] != available_states['idle']:
                msg_bin = f"Called startTraining from wrong state. First set backend to idle.".encode("utf-8")
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header("Content-type", "text/plain")
                self.send_header("Content-Length", len(msg_bin))
                self.end_headers()
                self.wfile.write(msg_bin)
                print("Called startInference from wrong state. First set backend to idle.")
                return
            
            # Decode params
            required_accuracy = float(params['required_accuracy'])
            if required_accuracy == -1:
                print("No specific accuracy was given by the user, targeting 100%")
                required_accuracy = 1
                
            timeout = int(float(params['training_timeout']))
            data_balance = float(params['data_balance'])
            
            # Send acknowledge response
            msg_bin = f"Called startTraining with: applicationName={params['applicationName']}".encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "text/plain")
            self.send_header("Content-Length", len(msg_bin))
            self.end_headers()
            self.wfile.write(msg_bin)
            
            # Update general Dict
            status_dict['current_state'] = available_states['train']
            status_dict['done'] = False
                
            if EMULATE_TRAINING:
                print(f"SIMULATOR: Called training for App: {params['applicationName']}")
                
                # Get Labels
                _ = requests.get(HMI_SERVER + 'getlabels?applicationname=' + params['applicationName'], verify=False)
                
                # Simulate time of creating dataset
                print(f"SIMULATOR: Creating Dataset for {params['applicationName']}")
                time.sleep(1)
                
                # Update App name in train dict
                train_dict['curr_app'] = params['applicationName']
                # Simulate train process
                epochs = 50
                print(f"SIMULATOR: Simulating training process for: {params['applicationName']}")
                for i in range(epochs):
                    train_dict['train_time_elapsed'] = i
                    train_dict['train_accuracy'] = (i/epochs)
                    train_dict['epoch'] = i
                    _ = requests.post(HMI_SERVER + 'postTrainingStatus', json=train_dict, verify=False)
                    time.sleep(0.2)

            else: # TODO
                pass
                # Create Dataset from HMI
                #_ = requests.post(HMI_SERVER + 'postLogMessage', json={"message_type":"Info", "message":"Getting images from server to create dataset"}, verify=False)
                #_ = requests.post(HMI_SERVER + 'postLogMessage', json={"message_type":"Info", "message":"Dataset created, starting training"}, verify=False)
                
                # Finetune the baseline model with new application
                #TrainThread = Process(target=Siamese_train, kwargs={\
                #    "model_load_path":MODEL_LOAD_PATH, "root_dir_train":DATA_ROOT_DIR +"/crops/" + params['applicationName'],\
                #    "model_workdir":DATA_ROOT_DIR + "/../../models_trained/" + params['applicationName'] + "/", "epochs":EPOCHS, "learning_rate":LEARNING_RATE,\
                #    "weight_decay":WEIGHT_DECAY, "io_dir":IO_DIR, "nio_dir":NIO_DIR, "valid_split":VALID_SPLIT, "dataset_mean":DATASET_MEAN, "dataset_std":DATASET_STD, "drop_rate":DROP_RATE,\
                #    "store_csv":STORE_CSV, "MultiThreadPipe":child_conn, "HmiServerAddr":HMI_SERVER, "train_dict":train_dict, "BackendSrv":BACKEND_SRV, "CurrApp":params['applicationName'],\
                #    "required_accuracy":required_accuracy, "timeout":timeout, "data_balance":data_balance})
                #TrainThread.start()

        elif '/startInference' in self.path or '/startinference' in self.path:
            # Parse Params
            i = self.path.index ( "?" ) + 1
            params = dict ( [ tuple ( p.split("=") ) for p in self.path[i:].split ( "&" ) ] )
            
            # Check call from right state
            if status_dict['current_state'] != available_states['idle']:
                msg_bin = f"Called startInference from wrong state. First set backend to idle.".encode("utf-8")
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header("Content-type", "text/plain")
                self.send_header("Content-Length", len(msg_bin))
                self.end_headers()
                self.wfile.write(msg_bin)
                print("Called startInference from wrong state. First set backend to idle.")
                return
            
            # Send acknowledge response
            msg_bin = f"Called startInference with: applicationName={params['applicationName']}".encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", "text/plain")
            self.send_header("Content-Length", len(msg_bin))
            self.end_headers()
            self.wfile.write(msg_bin)

            # Update general Dict
            status_dict['current_state'] = available_states['inference']
            
            # Check if App exists
            exists = False
            for app in status_dict['known_apps']:
                if app['name'] == params['applicationName']:
                    exists = True
                    break
            if not exists:
                # Go back to idle state
                status_dict['current_state'] = available_states['error']
                print(f"ERROR: {params['applicationName']} App doesn't exist yet. Cannot Start Inference!")
                
                # Send error info
                error_dict['current_error'] = 0
                _ = requests.post(HMI_SERVER + 'postError', json=error_dict, verify=False)
                _ = requests.post(HMI_SERVER + 'postLogMessage', json={"message_type":"Error", "message": str(params['applicationName']) + " application does not exist yet. Cannot Start Inference!"}, verify=False)
                
            else:
                        
                if EMULATE_INFERENCE:
                    # Simulate inference
                    print(f"SIMULATOR: Called inference for App: {params['applicationName']}")
                    
                    #Get ROIS
                    print(f"Getting ROIS for App: {params['applicationName']}")
                    _ = requests.get(HMI_SERVER + 'getRois?applicationname=' + params['applicationName'], verify=False)
                    
                    #Get Reference Image
                    print(f"SIMULATOR: Getting Reference image for App: {params['applicationName']}")
                    _ = requests.get(HMI_SERVER + 'getreferenceimage?applicationname=' + params['applicationName'], verify=False)
                        
                    how_many = 100
                    for i in range(how_many):
                        # Get live image and give it a tag
                        _ = requests.get(HMI_SERVER + 'getCameraImage?applicationName=' + params['applicationName'] + '&imageNr=' + str(i), verify=False)
                        # Simulate processing time
                        time.sleep(0.1)
                        
                        # Send inference result
                        inference_dict['curr_app'] = params['applicationName']
                        inference_dict['tag_last_inference'] = [ 0.85, 0.55, 0.99 ]
                        inference_dict['inference_result'] = [ 0.85, 0.55, 0.99 ]
                        _ = requests.post(HMI_SERVER + 'postInferenceStatus?imageNr=' + str(i), json=inference_dict, verify=False)
                        
                else: # TODO
                    pass
                    #if params['free_run'] == 'True' or params['free_run'] == 'true':
                    #    freerun = True
                    #else:
                    #    freerun = False
                        
                    #inf = Inference(modelPath=app['model_path'],\
                    #        currApp=params['applicationName'],\
                    #        getFromHmi=True,\
                    #        showOnHmi=True,\
                    #        HmiServerAddr=HMI_SERVER,\
                    #        useIolink=False,\
                    #        logResults=False,\
                    #        MultiThreadPipe=child_conn,\
                    #        freerun = freerun,\
                    #        )
                    #
                    #InfThread = Process(target=inf.run)
                    #InfThread.start()
                    
                
        elif '/setIdle' in self.path or '/setidle' in self.path:
            # Switch back to idle
            if status_dict['current_state'] == available_states['inference']:
                if InfThread.is_alive() :
                    print("Killing inference thread")
                    InfThread.kill() 
                if hasattr(InfThread, '__iter__') :
                    InfThread.join()
                print("Inference stopped, switching to idle")

            elif status_dict['current_state'] == available_states['train']:
                if TrainThread.is_alive() :
                    print("Sending Stop signal to training thread")
                    try:
                        print('sending:', {'Stop': 1})
                        parent_conn.send({'Stop':1})
                    except TimeoutError:
                            print('sending data timeout')
                        
                if hasattr(TrainThread, '__iter__') :
                    TrainThread.join()
                      
            # Switch back to idle and send response
            print(f"Switching back to idle")
            status_dict['current_state'] = available_states['idle']
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"Called setIdle".encode("utf-8"))
            
        elif '/triggerInference' in self.path or '/triggerinference' in self.path:
            
            # Check call from right state
            if status_dict['current_state'] != available_states['inference']:
                msg_bin = f"Called triggerInference from wrong state. You have to start an inference first with free_run=False.".encode("utf-8")
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header("Content-type", "text/plain")
                self.send_header("Content-Length", len(msg_bin))
                self.end_headers()
                self.wfile.write(msg_bin)
                print("Called triggerInference from wrong state. You have to start an inference first with free_run=False.")
                return
            else:
                print("Triggering new image")
                print('sending:', {'NextImg':1})
                parent_conn.send({'NextImg':1})

            # Send response
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"Called triggerInference".encode("utf-8"))

        elif '/finishTraining' in self.path:
            # Note we end up here if the training process was not interrupted by calling setIdle. In such case, the AI-Training thread makes a call
            # over this get https instruction to share the training results with the backend server
            
            # Check call from right state
            if status_dict['current_state'] != available_states['train']:
                msg_bin = f"Called saveApp from wrong state. You have to trigger a training process.".encode("utf-8")
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header("Content-type", "text/plain")
                self.send_header("Content-Length", len(msg_bin))
                self.end_headers()
                self.wfile.write(msg_bin)
                print("Called finishTraining from wrong state. First start a training process.")
                return
            
            # Parse Params
            i = self.path.index ( "?" ) + 1
            params = dict ( [ tuple ( p.split("=") ) for p in self.path[i:].split ( "&" ) ] )
            
            if int(params['Timeout']) == 0:
                # Update known applications
                exists = False
                for index, app in enumerate(status_dict['known_apps']):
                    if app['name'] == params['applicationName']:
                        exists = True
                        break
                if not exists:
                    print(f"Application: {params['applicationName']} doesn't exist yet. Adding it!")
                    status_dict['known_apps'].append({"name": params['applicationName'], "accuracy": params['Accuracy'], "timestamp": str(datetime.utcnow().isoformat(sep=' ', timespec='milliseconds')), "model_path":params['ModelPath']})
                else:
                    print(f"Application: {params['applicationName']} already exists. Overwriting it!")
                    status_dict['known_apps'][index] = {"name": params['applicationName'], "accuracy": params['Accuracy'], "timestamp": str(datetime.utcnow().isoformat(sep=' ', timespec='milliseconds')), "model_path":params['ModelPath']}
                
                # Save updated known-apps dictionary
                print("Writing list of known apps persistently to disk")
                with open(STATUS_FILE, 'w') as file:
                    general_dict['general_status']['known_apps'] = status_dict['known_apps']
                    json.dump(general_dict, file, ensure_ascii=False, indent=4)
            else:
                print("Training process timed out. Application not saved.")
                _ = requests.post(HMI_SERVER + 'postLogMessage', json={"message_type":"Error", "message": "Training process timed out. Application not saved."}, verify=False)

            # Switch back to idle and send response
            print(f"Switching back to idle")
            status_dict['current_state'] = available_states['idle']
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"Called saveApp".encode("utf-8"))

if __name__ == "__main__":
    httpd = HTTPServer((BACKEND_IP, BACKEND_PORT), Serv)
    httpd.serve_forever()