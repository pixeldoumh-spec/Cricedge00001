import fastapi
from fastapi import HTTPException
import os
from datetime import datetime, timezone

@fastapi.router.get("/health")
async def health_check():
    """
    Health check endpoint that returns API status and model information.
    """
    try:
        from pymongo import MongoClient
        from cric_model import load_artifact
        
        client = MongoClient(os.environ.get("MONGO_URL"), serverSelectionTimeoutMS=3000)
        db = client[os.environ.get("DB_NAME")]
        artifact = load_artifact(db, force=False)

        model_info = {
            "version": artifact.get("version") if artifact else "not_trained",
            "trained_at": artifact.get("trained_at") if artifact else None,
            "matches_ingested": artifact.get("matches_ingested") if artifact else 0,
            "training_samples": artifact.get("training_samples") if artifact else 0,
            "formats": {
                fmt: stats.get("metrics", {})
                for fmt, stats in (artifact.get("formats") or {}).items()
            }
            if artifact
            else {},
        }

        return {
            "status": "online",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model_info,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@fastapi.router.post("/admin/train-model")
async def trigger_model_training():
    """
    Trigger a full model retraining (admin endpoint).
    Requires authentication in production.
    """
    try:
        from pymongo import MongoClient
        import cric_model

        client = MongoClient(os.environ.get("MONGO_URL"), serverSelectionTimeoutMS=5000)
        db = client[os.environ.get("DB_NAME")]

        result = cric_model.build_and_train(db)

        return {
            "status": "training_completed",
            "artifact": {
                "version": result.get("version"),
                "trained_at": result.get("trained_at"),
                "matches_ingested": result.get("matches_ingested"),
                "training_samples": result.get("training_samples"),
                "formats": {
                    fmt: stats.get("metrics")
                    for fmt, stats in result.get("formats", {}).items()
                },
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")
