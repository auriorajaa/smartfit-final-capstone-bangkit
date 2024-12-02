from diagrams import Cluster, Diagram
from diagrams.gcp.compute import AppEngine
from diagrams.gcp.database import Firebase
from diagrams.gcp.devtools import ContainerRegistry
from diagrams.gcp.ml import AIPlatform
from diagrams.gcp.storage import GCS

with Diagram("ML Model Deployment Architecture", show=False, direction="LR"):
    # ML Team's Model
    with Cluster("Machine Learning Team"):
        ml_model = AIPlatform("ML Model", fontweight="normal")

    # Storage and Registry
    with Cluster("Storage & Registry"):
        storage = GCS("Cloud Storage\n(Public Model)", fontweight="normal")
        registry = ContainerRegistry("Artifact Registry", fontweight="normal")

    # Backend Service
    with Cluster("Backend Service"):
        app_engine = AppEngine("App Engine", fontweight="normal")

    # Database
    with Cluster("Database"):
        firebase = Firebase("Firebase\n(User History)", fontweight="normal")

    # Flow
    ml_model >> storage
    storage >> app_engine
    registry >> app_engine
    app_engine >> firebase
