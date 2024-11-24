from diagrams import Cluster, Diagram
from diagrams.gcp.compute import Run
from diagrams.gcp.database import Firestore
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
        cloud_run = Run("Cloud Run", fontweight="normal")

    # Database
    with Cluster("Database"):
        firestore = Firestore("Firestore\n(User History)", fontweight="normal")

    # Flow
    ml_model >> storage
    storage >> cloud_run
    registry >> cloud_run
    cloud_run >> firestore
