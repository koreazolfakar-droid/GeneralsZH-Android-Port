package com.generalsx.zerohour;

import java.nio.charset.StandardCharsets;
import java.security.AlgorithmParameters;
import java.security.KeyFactory;
import java.security.PublicKey;
import java.security.Signature;
import java.security.interfaces.ECPublicKey;
import java.security.spec.ECGenParameterSpec;
import java.security.spec.ECParameterSpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;

// GeneralsX @feature Codex 06/10/2026 Pin our update identity; accept public P-256 keys only.
final class UpdateTrust {
    static final String BASE_URL =
        "https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/";
    static final String PUBLIC_KEY_ASSET = "update-public.pem";
    static final String CHANNEL = "koreazolfakar-droid/mobile-v4/v1";

    private UpdateTrust() { }

    static PublicKey publicKey(byte[] pem) throws Exception {
        String text = new String(pem, StandardCharsets.US_ASCII).trim();
        String begin = "-----BEGIN PUBLIC KEY-----";
        String end = "-----END PUBLIC KEY-----";
        if (!text.startsWith(begin) || !text.endsWith(end) || text.contains("PRIVATE")) {
            throw new IllegalArgumentException("Expected public SPKI PEM only");
        }
        byte[] der = Base64.getDecoder().decode(
            text.substring(begin.length(), text.length() - end.length()).replaceAll("\\s", ""));
        PublicKey key = KeyFactory.getInstance("EC").generatePublic(new X509EncodedKeySpec(der));
        AlgorithmParameters parameters = AlgorithmParameters.getInstance("EC");
        parameters.init(new ECGenParameterSpec("secp256r1"));
        ECParameterSpec expected = parameters.getParameterSpec(ECParameterSpec.class);
        ECParameterSpec actual = ((ECPublicKey) key).getParams();
        if (!actual.getCurve().equals(expected.getCurve())
                || !actual.getGenerator().equals(expected.getGenerator())
                || !actual.getOrder().equals(expected.getOrder())
                || actual.getCofactor() != expected.getCofactor()) {
            throw new IllegalArgumentException("Update key must use ECDSA P-256");
        }
        return key;
    }

    static boolean verify(byte[] pem, byte[] data, byte[] signatureText) {
        try {
            Signature verifier = Signature.getInstance("SHA256withECDSA");
            verifier.initVerify(publicKey(pem));
            verifier.update(data);
            return verifier.verify(Base64.getDecoder().decode(
                new String(signatureText, StandardCharsets.US_ASCII).trim()));
        } catch (Exception invalid) {
            return false;
        }
    }
}
