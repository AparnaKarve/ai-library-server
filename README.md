# Setup

- Create a namespace (say, `argo-rest-server`)
    
  `oc new-project argo-rest-server`
  
- Add `admin` role to `default` service account for this project

  `oc policy add-role-to-user admin system:serviceaccount:argo-rest-server:default`
  
- Create a Secret in this project for the S3 credentials


- ##### Building the sources and Deployment (if using github)

    ```
    oc new-project builfactory
    
    oc create -f ./build_and_deploy/argo-rest-server-build.yaml
    
    oc new-app --template builder-argo-rest-server
    
    oc project argo-rest-server
    
    oc create -f ./build_and_deploy/argo-rest-server-deploy.yaml
    
    oc new-app --template argo-rest-server
    
    ```
    
- ##### Building the sources and Deployment (if using gitlab)

    ```
    
    oc create -f ./build_and_deploy/argo-rest-server-deploy-with-quay.yaml
    
    oc new-app --template argo-rest-server
    
    ```    
    
Argo REST Server uses the Argo CLI command to submit workflows.


### Argo REST Server API Endpoints:
- `GET /status`

   Gets the status of the service
   
- `POST /training-jobs`

    Submits a Training job workflow.
    
    JSON Parameter `"quick-submit": "Y"` can be passed if a workflow merely needs to be submitted without further monitoring. With the `quick-submit` option specified, the POST call will return immediately.
    
- `POST /prediction-jobs`

    Submits a Prediction job workflow.    
    
- `GET /training-jobs`

    Gets all training jobs
    
- `GET /jobs/<workflow_id>`

    Gets the specified training job details    
    
    
      
### Curl Examples on how to use the API Endpoints

- `GET /status`

  `curl  http://host/status`
  
  **Response JSON**
  
  ```
  {
    "message":"Up and Running",
    "status":"Success"
  }
  ```
  
---------

- `POST /training-jobs`

    The `POST /training-jobs` endpoint can be called in two ways, depending on where the workflow exists.
    
    - If the workflow file resides on the Argo REST Server, you can specify the workflow file(with it's path included) in the `workflow` parameter, as shown below -
    
        ```
        curl -H "Accept: application/json" -d '{ "workflow": "<workflow_on_server>.yaml", "namespace": "<namespace>" }' http://<host>/training-jobs | python -m json.tool
        ```
        
        Additional parameters specific to the workflow (such as bucket name), could also be specified as shown below -
        ```
        curl -H "Accept: application/json" -d '{ "workflow": "<workflow_on_server>.yaml", "namespace": "<namespace>", "bucket": "<my-bucket>" }' http://<host>/training-jobs | python -m json.tool
        ```
    
    - If the workflow file does not reside on the Argo REST Server, use the following command -
    
        ```
        curl -H "Content-Type: multipart/mixed" -F "workflow=@<workflow>.yaml" -F "parameters={ "namespace": "<namespace>", "bucket": "<my-bucket>" }" http://<host>/training-jobs | python -m json.tool
        ```

    **Response JSON**
  
  ```
   "workflow_response": {
        "Info": {
            "creationTimestamp": "2019-09-13T15:25:35Z",
            "generateName": "flakestrain",
            "generation": 1,
            "labels": {
                "workflows.argoproj.io/completed": "true",
                "workflows.argoproj.io/phase": "Succeeded"
            },
            "name": "flakestrainxdpt2",
            "namespace": "ai-library-server",
            "resourceVersion": "17630286",
            "selfLink": "/apis/argoproj.io/v1alpha1/namespaces/ai-library-server/workflows/flakestrainxdpt2",
            "uid": "bb95a65a-d63a-11e9-b199-26ba81be99c4"
        },
        "Per_Step_Output": {
            "flakestrainxdpt2": {
                "message": "No info available",
                "outputs": {
                    "artifact_type": "No artifacts info available"
                },
                "phase": "Succeeded"
            },
            "flakestrainxdpt2.Flakes-Train": {
                "message": "No info available",
                "outputs": {
                    "artifact_type": "S3",
                    "bucket": "DH-DEV-DATA",
                    "endpoint-url": "s3.upshift.redhat.com",
                    "key": "chadtest/fromargo/flake/model-output-bb95a65a-d63a-11e9-b199-26ba81be99c4.tgz"
                },
                "phase": "Succeeded"
            }
        }
    }
  ```
  
  The `Per_Step_Output` provides Output info per step in the workflow.
  
    NOTE: Specify the `"quick-submit": "Y"` parameter for a quick submit in case the output artifacts information is not needed. 
            
    **Response JSON with `quick-submit`**
  
  ```
  {
    "creationTimestamp": "2019-09-13T16:52:48Z",
    "generateName": "flakestrain",
    "generation": 1,
    "name": "flakestrain27vv7",
    "namespace": "my-namespace",
    "resourceVersion": "17644829",
    "selfLink": "/apis/argoproj.io/v1alpha1/namespaces/ai-library-server/workflows/flakestrain27vv7",
    "uid": "ea8cb9a9-d646-11e9-b199-26ba81be99c4"
  }
  ```  
        
----- 

- `POST /prediction-jobs`

   curl commands are identical to `POST /training-jobs` (see above)

    **Response JSON**
  
  ```
   {
    "workflow_response": {
        "Info": {
            "creationTimestamp": "2019-10-15T23:56:05Z",
            "generateName": "anomalydetectionpredict",
            "generation": 1,
            "labels": {
                "jobType": "prediction",
                "workflows.argoproj.io/completed": "true",
                "workflows.argoproj.io/phase": "Succeeded"
            },
            "name": "anomalydetectionpredictcbbk6",
            "namespace": "ak-project",
            "resourceVersion": "24050733",
            "selfLink": "/apis/argoproj.io/v1alpha1/namespaces/ak-project/workflows/anomalydetectionpredictcbbk6",
            "uid": "5988990f-efa7-11e9-ac81-64006a625e19"
        },
        "Per_Step_Output": {
            "anomalydetectionpredictcbbk6": {
                "message": "No info available",
                "outputs": {
                    "artifact_type": "No artifacts info available"
                },
                "phase": "Succeeded"
            },
            "anomalydetectionpredictcbbk6.Anomaly-Detection-Predict": {
                "message": "No info available",
                "outputs": {
                    "artifact_type": "S3",
                    "bucket": "DH-DEV-DATA",
                    "endpoint-url": "s3.upshift.redhat.com",
                    "key": "akarvetest/fromargo/anomalydetection/result-output-5988990f-efa7-11e9-ac81-64006a625e19.tgz"
                },
                "phase": "Succeeded"
            }
        }
    }
    ```
 

------  
         
- `GET /jobs/<workflow_id>` 
    
    ```
    curl http://<host>/jobs/flakestrainxdpt2 | python -m json.tool
    ```
    
    ```
    curl -X GET -H "Content-Type: application/json" http://<host>/jobs/flakestrainxdpt2 -d '{"namespace": "argo-rest-server"}'| python -m json.tool
    ```
    
    **Response JSON**
  
  ```
   "workflow_response": {
        "Info": {
            "creationTimestamp": "2019-09-13T15:25:35Z",
            "generateName": "flakestrain",
            "generation": 1,
            "labels": {
                "workflows.argoproj.io/completed": "true",
                "workflows.argoproj.io/phase": "Succeeded"
            },
            "name": "flakestrainxdpt2",
            "namespace": "ai-library-server",
            "resourceVersion": "17630286",
            "selfLink": "/apis/argoproj.io/v1alpha1/namespaces/ai-library-server/workflows/flakestrainxdpt2",
            "uid": "bb95a65a-d63a-11e9-b199-26ba81be99c4"
        },
        "Per_Step_Output": {
            "flakestrainxdpt2": {
                "message": "No info available",
                "outputs": {
                    "artifact_type": "No artifacts info available"
                },
                "phase": "Succeeded"
            },
            "flakestrainxdpt2.Flakes-Train": {
                "message": "No info available",
                "outputs": {
                    "artifact_type": "S3",
                    "bucket": "DH-DEV-DATA",
                    "endpoint-url": "s3.upshift.redhat.com",
                    "key": "chadtest/fromargo/flake/model-output-bb95a65a-d63a-11e9-b199-26ba81be99c4.tgz"
                },
                "phase": "Succeeded"
            }
        }
    }
  ```
  


-----        
- `GET /training-jobs` 
    
    ```
    curl http://<host>/training-jobs | python -m json.tool
    ```
    
    ```
    curl -X GET -H "Content-Type: application/json" http://<host>/training-jobs -d '{"namespace": "argo-rest-server"}'| python -m json.tool
    ```
    
    **Response JSON**
  
  ```
   "training_jobs_response": {
        "anomalydetectiontrain5cbhk": {
            "Info": {
                "creationTimestamp": "2019-09-20T20:16:02Z",
                "generateName": "anomalydetectiontrain",
                "generation": 1,
                "labels": {
                    "jobType": "training",
                    "workflows.argoproj.io/completed": "true",
                    "workflows.argoproj.io/phase": "Succeeded"
                },
                "name": "anomalydetectiontrain5cbhk",
                "namespace": "ak-project",
                "resourceVersion": "19299195",
                "selfLink": "/apis/argoproj.io/v1alpha1/namespaces/ak-project/workflows/anomalydetectiontrain5cbhk",
                "uid": "77d186c8-dbe3-11e9-ac81-64006a625e19"
            },
            "Per_Step_Output": {
                "anomalydetectiontrain5cbhk": {
                    "message": "No info available",
                    "outputs": {
                        "artifact_type": "No artifacts info available"
                    },
                    "phase": "Succeeded"
                },
                "anomalydetectiontrain5cbhk.Anomaly-Detection-Train": {
                    "message": "No info available",
                    "outputs": {
                        "artifact_type": "S3",
                        "bucket": "ak-s3-reject",
                        "endpoint-url": "s3.amazonaws.com",
                        "key": "akarvetest/fromargo/anomaly-detection/model-output-77d186c8-dbe3-11e9-ac81-64006a625e19.tgz"
                    },
                    "phase": "Succeeded"
                }
            }
        },
        "flakestrain74vrb": {
            ...
            ...
        }
   }     
  ```
  
- `GET /prediction-jobs` 
    
    ```
    curl http://<host>/prediction-jobs | python -m json.tool
    ```
    
    ```
    curl -X GET -H "Content-Type: application/json" http://<host>/prediction-jobs -d '{"namespace": "argo-rest-server"}'| python -m json.tool
    ```
    
    **Response JSON**
  
  ```
   "prediction_jobs_response": {
        "anomalydetectionpredict4dxfj": {
            "Info": {
                "creationTimestamp": 2019-09-24T20:45:48Z",
                "generateName": "anomalydetectionpredict",
                "generation": 1,
                "labels": {
                    "jobType": "prediction",
                    "workflows.argoproj.io/completed": "true",
                    "workflows.argoproj.io/phase": "Succeeded"
                },
                "name": "anomalydetectionpredict4dxfj",
                "namespace": "ak-project",
                "resourceVersion": "19299195",
                "selfLink": "/apis/argoproj.io/v1alpha1/namespaces/ak-project/workflows/anomalydetectionpredict4dxfj",
                "uid": "77d186c8-dbe3-11e9-ac81-64006a625e19"
            },
            "Per_Step_Output": {
                "anomalydetectionpredict4dxfj": {
                    "message": "No info available",
                    "outputs": {
                        "artifact_type": "No artifacts info available"
                    },
                    "phase": "Succeeded"
                },
                "anomalydetectionpredict4dxfj.Anomaly-Detection-Predict": {
                    "message": "No info available",
                    "outputs": {
                        "artifact_type": "S3",
                        "bucket": DH-DEV-DATA",
                        "endpoint-url": s3.upshift.redhat.com",
                        "key": akarvetest/fromargo/anomaly-detection/results-49e8ec90-df0c-11e9-ac81-64006a625e19.tgz"
                    },
                    "phase": "Succeeded"
                }
            }
        },
        "anomalydetectionpredict6hx4c": {
            ...
            ...
        }
   }     
  ```  
