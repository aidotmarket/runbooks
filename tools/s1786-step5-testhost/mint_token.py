"""Local P-256 private key and short-lived token; never print either."""
import argparse
import json
import os
import time
from pathlib import Path
from uuid import uuid4
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

def private_write(path, data):
    fd=os.open(path, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(data)

def mint(fixtures, directory):
    directory=Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    keyfile=directory/"private.pem"
    if keyfile.exists():
        key=serialization.load_pem_private_key(keyfile.read_bytes(), password=None)
    else:
        key=ec.generate_private_key(ec.SECP256R1())
        private_write(keyfile, key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode())
    if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
        raise ValueError("Expected local EC P-256 key")
    jwk=json.loads(jwt.algorithms.ECAlgorithm.to_jwk(key.public_key()))
    jwk.update(alg="ES256", use="sig", kid="s1786-step5-local")
    (directory/"jwks.json").write_text(json.dumps({"keys":[jwk]}))
    ids=json.loads(Path(fixtures).read_text())
    now=int(time.time())
    claims=dict(iss="https://auth.ai.market", aud="https://connect.ai.market/mcp", sub=ids["user_id"], gid=ids["grant_id"], jti=uuid4().hex, client_id=ids["client_id"], scope="market.read account.read", iat=now, nbf=now, exp=now+600)
    private_write(directory/"token.jwt", jwt.encode(claims, key, algorithm="ES256", headers={"typ":"at+jwt", "kid":"s1786-step5-local"}))
    print("Wrote local private.pem (0600), public jwks.json and token.jwt (0600); expires in 10 minutes; no token printed")

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixtures", required=True)
    p.add_argument("--key-dir", required=True)
    a=p.parse_args()
    mint(a.fixtures, a.key_dir)
