with open("startup.sh", "w") as f:
    f.write("""#!/bin/bash
uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
""")
print("✅ startup.sh 업데이트 완료")
