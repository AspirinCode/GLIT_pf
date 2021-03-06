import uvicorn
from fastapi import FastAPI, APIRouter, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import List
#from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import PlainTextResponse

import server_fastapi_router
from fastapi import File, Form, UploadFile

import time

from model_serve import Model_serve

model = Model_serve()




class InputData(BaseModel):
    ecfp: List[float]
    gex: List[float]
    dosage: float
    duration: int
    drugname: str
    cellline: str


app = FastAPI()
#app.include_router(server_fastapi_router, prefix='/glit')


"""
@app.get("/healthcheck", status_code=200)
async def root():
    return "Inference implementation of GLIT on FastAPI"
"""

@app.get("/")
def root():
    print("Inference Implementation of GLIT on FsatAPI")
    return "Inference implementation of GLIT on FastAPI"

#   Post not using pydantic


#   Post using pydantic
@app.post('/glit_predict/')
#@app.post('/glit_predict/{request}')
async def glit_predict(request: dict):

    
    t = time.time() # get execution time

    request_dict = request
    
    ecfp = request_dict['ecfp']
    gex = request_dict['gex']
    dosage = request_dict['dosage']
    duration = request_dict['duration']
    drugname = request_dict['drugname']

    result = model.predict(ecfp, gex, dosage, duration)
    result = float(result[0][1])


    dt = time.time() - t

#    return jsonify({'ecfp': ecfp[0], 'gex':gex[0], 'dosage':dosage, 'duration':duration, 'drugname':drugname, 'predicted_prob':result})
#    return JSONResponse(content = {'ecfp': ecfp[0], 'gex':gex[0], 'dosage':dosage, 'duration':duration, 'drugname':drugname, 'predicted_prob':result})
    return {'ecfp': ecfp[0], 'gex':gex[0], 'dosage':dosage, 'duration':duration, 'drugname':drugname, 'predicted_prob':result}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=400)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


if __name__ == "__main__":
    HOST = 'localhost'
    PORT = 8080

    uvicorn.run(app, host = HOST, port = PORT)

"""
def glit_predict(request: InputData):
    
    print(request)

    print(request.body())
    print(request.json())
    print(request.form())

#    json_compatible_item_data = jsonable_encoder(Request)
    json_compatible_item_data = jsonable_encoder(request.json())
    print(json_compatible_item_data)

    return JSONResponse(content=json_compatible_item_data)
"""




"""
#@app.post('/glit_predict')
@app.get('/glit_predict')
#@app.route('/glit_predict', method=['GET', 'POST'])
#def glit_predict(request: dict):
def glit_predict(request: Request):
    print(request)
    json_compatible_item_data = jsonable_encoder(Request)
    print(json_compatible_item_data)

    return JSONResponse(content=json_compatible_item_data)
"""
    
     

"""
def glit_predict(ecfp: ):
    t = time.time() # get execution time

#    if flask.request.method == 'GET':
    
    ecfp = flask.request.form.getlist('ecfp')
    gex = flask.request.form.getlist('gex')
    dosage = flask.request.form.get('dosage')
    duration = flask.request.form.get('duration')
    drugname = flask.request.form.get('drugname')

    result = model.predict(ecfp, gex, dosage, duration)
    result = float(result[0][1])


    dt = time.time() - t
    app.logger.info("Execution time: %0.02f seconds" % (dt))

    return jsonify({'ecfp': ecfp[0], 'gex':gex[0], 'dosage':dosage, 'duration':duration, 'drugname':drugname, 'predicted_prob':result})
"""
"""
#   Using GET method, and List from typing
@app.get('/glit_predict/')
async def glit_predict(ecfp: List[int], gex: List[float], dosage: float, duration: int, drugname: str, cellline: str):

    result = model.predict(ecfp, gex, dosage, duration)
    result = float(result[0][1])


    dt = time.time() - t

#    return jsonify({'ecfp': ecfp[0], 'gex':gex[0], 'dosage':dosage, 'duration':duration, 'drugname':drugname, 'predicted_prob':result})
#    return JSONResponse(content = {'ecfp': ecfp[0], 'gex':gex[0], 'dosage':dosage, 'duration':duration, 'drugname':drugname, 'predicted_prob':result})
    return {'ecfp': ecfp[0], 'gex':gex[0], 'dosage':dosage, 'duration':duration, 'drugname':drugname, 'predicted_prob':result}

"""

