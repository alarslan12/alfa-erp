"""Trusted Firebase RTDB administration helper for Cloud Shell (not bundled).

Requires Google Application Default Credentials and firebase-admin installed.
Never run with a service-account JSON key checked into the repository.
"""
PROJECT_ID="alfa-erp-8700c"
WORKSPACE_ID="e2fc57b1-ef52-47b2-a6c9-ecd2e3832756"
DATABASE_URL="https://alfa-erp-8700c-default-rtdb.europe-west1.firebasedatabase.app"

def reference(node=""):
    import firebase_admin
    from firebase_admin import credentials, db
    try:
        app=firebase_admin.get_app('alfa-erp-admin-tools')
    except ValueError:
        app=firebase_admin.initialize_app(
            credentials.ApplicationDefault(),
            {"projectId":PROJECT_ID,"databaseURL":DATABASE_URL},
            name='alfa-erp-admin-tools')
    path="alfa/"+WORKSPACE_ID+("/"+str(node).strip("/") if node else "")
    return db.reference(path,app=app)

def read(node):
    return reference(node).get()
