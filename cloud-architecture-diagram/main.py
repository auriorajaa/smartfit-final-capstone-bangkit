from diagrams import Diagram, Cluster
from diagrams.gcp.ml import AIPlatform
from diagrams.gcp.devtools import ContainerRegistry
from diagrams.firebase.develop import RealtimeDatabase
from diagrams.gcp.compute import AppEngine
from diagrams.gcp.storage import Storage
from diagrams.onprem.client import Users

# Membuat diagram
with Diagram(
    "Outfit Recommendation System",
    show=True,
    direction="LR"
):
    # User interaction
    user = Users("User")

    # Google Cloud services cluster
    with Cluster("Google Cloud Platform"):
        backend = AppEngine("Backend Service")
        storage = Storage("Cloud Storage")
        model_registry = ContainerRegistry("Artifact Registry")
        ml_model = AIPlatform("ML Model")
        firebase_db = RealtimeDatabase("Firebase Database")

    # Data flow
    user >> backend
    backend >> storage
    backend >> model_registry >> ml_model
    ml_model >> backend >> firebase_db
    backend >> user
