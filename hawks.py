import os
import asyncio
import random
import logging
import json
import subprocess

from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device.aio import ProvisioningDeviceClient
from azure.iot.device import Message, MethodResponse
from datetime import timedelta, datetime
from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry, Region
from msrest.authentication import ApiKeyCredentials
import cv2 
import os, time, uuid

logging.basicConfig(level=logging.ERROR)

wait1=0

while wait1!=60:
    wait2=0
    while wait2!=1000000:
        wait2+=1
    wait1+=1




model_id = "dtmi:azurertos:devkit:gsgstml4s5;2" 

training_key = "20808934e22042999924f18536780e19"
ENDPOINT = "https://vision1lai.cognitiveservices.azure.com/"
prediction_key = "257bd71ec1e54e3ea0c712a7bffe8508"
PREDICTION_ENDPOINT = "https://vision1lai-prediction.cognitiveservices.azure.com/"
prediction_resource_id = "/subscriptions/61f501d2-1d9a-4626-bb0e-fe6661dfb8f3/resourceGroups/IOTC/providers/Microsoft.CognitiveServices/accounts/Vision1lai-Prediction"

credentials = ApiKeyCredentials(in_headers={"Training-key": training_key})
trainer = CustomVisionTrainingClient(ENDPOINT, credentials)
prediction_credentials = ApiKeyCredentials(in_headers={"Prediction-key": prediction_key})
predictor = CustomVisionPredictionClient(PREDICTION_ENDPOINT, prediction_credentials)

LAI_project_id = '1dc645a1-a66b-4298-8007-3ec782dd6d72'

LAI = trainer.get_project(LAI_project_id)

animal_classifier_id = '293e161d-d5d2-4596-a642-10641fc2c522'

animal_classifier = trainer.get_project(animal_classifier_id)

base_image_location = os.path.join(os.path.dirname(__file__) , 'images')

dispW = 1280
dispH = 720
flip = 2

payload ={
    "geoTag":{
        "lat" : 28.45086,
        "lon" : 77.28362,
    },
    "PredictionResult" : 0
}

camSet='nvarguscamerasrc ! video/x-raw(memory:NVMM), width=3264, height=2464, format=NV12, framerate=21/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'

# cam = cv2.VideoCapture(camSet)

# print(base_image_location)
async def send_telemetry_form(device_client,telemetry_msg):
    msg = Message(json.dumps(telemetry_msg))
    msg.content_encoding = "utf-8"
    msg.content_type = "application/json"
    print("Sent Message")
    await device_client.send_message(msg)

def stdin_listener():
    while True:
        selection = input("Press Q to quit\n")
        if selection == "Q" or selection =="q":
            print("Quitting...")
            break

async def provsion_device(provisioning_host, id_scope , registration_id , symmetric_key , model_id):
    prov_device = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host = "global.azure-devices-provisioning.net",
        registration_id = registration_id,
        id_scope = id_scope,
        symmetric_key = symmetric_key,
    )
    prov_device.provisioning_payload = {"modelId" : model_id}
    return await prov_device.register()


async def takePhoto(device_client):
    cam = cv2.VideoCapture(camSet)

    if not cam.isOpened():
        print("Error: Could not open camera")
        exit()

    ret , frame = cam.read()

    if not ret:
        print("Error : Could not read frame.")
        exit()


    cv2.imwrite("/home/haricharan/Desktop/python_codes/images/test_image.jpg",frame)

    cam.release()
    with open("/home/haricharan/Desktop/python_codes/images/test_image.jpg", 'rb') as image_data:
        idx = 0
        print(image_data)
        results = predictor.classify_image(LAI.id , 'LAI',image_data.read())
        print("Leaf Classification Results :\n")
        for prediction in  results.predictions:
                print("\t" + prediction.tag_name + ": {0:.2f}% ".format(prediction.probability * 100 ))
        image_data.close()

        if results.predictions[0].tag_name == 'healthy':
            payload['PredictionResult'] = 1
        else:
            payload['PredictionResult'] = 0

        await send_telemetry_form(device_client , payload)
    # with open("/home/haricharan/Desktop/python_codes/images/test_image.jpg","rb") as image_contents:
    #     results1 = predictor.classify_image(animal_classifier.id , "animal_classifier" , image_contents.read())
    #     for prediction in results1.predictions:
    #         print("\t" + prediction.tag_name + ": {0:.2f}%".format(prediction.probability * 100))

async def main():
    provisioning_host = "global.azure-devices-provisioning.net"
    id_scope = "0ne00B45454"
    registration_id = "iotjetson1"
    symmetric_key = "EBw6Iosb0hXUWFAcvm6/dgqJslpwxoNJlkeFpkai4K8="

    reg_res = await provsion_device(provisioning_host , id_scope , registration_id , symmetric_key , model_id)

    if(reg_res.status == "assigned"):
        print("Device was assigned")
        print(reg_res.registration_state.assigned_hub)
        print(reg_res.registration_state.device_id)

        device_client = IoTHubDeviceClient.create_from_symmetric_key(
            symmetric_key = symmetric_key,
            hostname = reg_res.registration_state.assigned_hub,
            device_id = reg_res.registration_state.device_id,
            product_info = model_id,
        )
    else:
        raise RuntimeError(
            "Could not provision device .Aborting Plug and Play device connection"
        )


    await device_client.connect()


    # print(LAI.id)
    # print(animal_classifier.id)
    # print(os.path.join(base_image_location , "test_image.jpg_8360_s00_00000.jpg"))
    
    
                                        
    count=0
    while True:
        while count!=80000000:
            count+=1
        await takePhoto(device_client)
        # await send_telemetry()
        count=0
    # send_telemetry_task = asyncio.ensure_future(send_telemetry())
    # loop = asyncio._get_running_loop()

    # user_finished = loop.run_in_executor(None , stdin_listener)
    # await user_finished
    # send_telemetry_task.cancel()


    await device_client.shutdown()
        





if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()



