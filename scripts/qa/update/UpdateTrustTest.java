package com.generalsx.zerohour;

import java.nio.charset.StandardCharsets;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.Signature;
import java.security.spec.ECGenParameterSpec;
import java.util.Base64;

// Tests use newly generated in-memory keys only; no operator secret is used or exported.
public final class UpdateTrustTest {
    private static int tests;
    private static void require(boolean valid, String name) {
        if (!valid) throw new AssertionError(name);
        tests++;
    }
    private static KeyPair pair(String curve) throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("EC");
        generator.initialize(new ECGenParameterSpec(curve));
        return generator.generateKeyPair();
    }
    private static byte[] pem(KeyPair pair) {
        return ("-----BEGIN PUBLIC KEY-----\n" + Base64.getEncoder().encodeToString(pair.getPublic().getEncoded())
            + "\n-----END PUBLIC KEY-----\n").getBytes(StandardCharsets.US_ASCII);
    }
    private static byte[] sign(KeyPair key, byte[] data) throws Exception {
        Signature signer = Signature.getInstance("SHA256withECDSA");
        signer.initSign(key.getPrivate()); signer.update(data);
        return Base64.getEncoder().encode(signer.sign());
    }
    public static void main(String[] args) throws Exception {
        KeyPair ours = pair("secp256r1"), wrong = pair("secp256r1"), otherCurve = pair("secp384r1");
        byte[] body = "{\"schema\":1,\"serial\":1}".getBytes(StandardCharsets.UTF_8);
        byte[] sig = sign(ours, body);
        require(UpdateTrust.verify(pem(ours), body, sig), "own P-256 signature");
        require(!UpdateTrust.verify(pem(wrong), body, sig), "wrong identity");
        require(!UpdateTrust.verify(pem(ours), "tampered".getBytes(StandardCharsets.UTF_8), sig), "tampered manifest");
        require(!UpdateTrust.verify(pem(ours), body, "bad-base64!".getBytes(StandardCharsets.US_ASCII)), "malformed signature");
        require(!UpdateTrust.verify(pem(otherCurve), body, sign(otherCurve, body)), "wrong EC curve");
        byte[] privateKey = ("-----BEGIN PRIVATE KEY-----\n" + Base64.getEncoder().encodeToString(ours.getPrivate().getEncoded())
            + "\n-----END PRIVATE KEY-----").getBytes(StandardCharsets.US_ASCII);
        require(!UpdateTrust.verify(privateKey, body, sig), "private PEM forbidden");
        require(!UpdateTrust.verify(new byte[0], body, sig), "absent trust root fails closed");
        require(!UpdateTrust.BASE_URL.contains("MYSOREZ") && UpdateTrust.BASE_URL.endsWith("/updates/"), "own endpoint");
        System.out.println("PASS: " + tests + " production UpdateTrust crypto checks");
    }
}
