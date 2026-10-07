#pragma once
// GeneralsX @bugfix Codex 07/10/2026 Verify Online TLS and use Android's actual system roots, never an insecure fallback.
#include <curl/curl.h>
#if defined(__ANDROID__) || defined(GX_TEST_ANDROID_TLS)
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <openssl/ssl.h>
#include <openssl/pem.h>
#include <openssl/err.h>

inline unsigned GXLoadSystemCertificateDirectory(X509_STORE* store, const char* path)
{
    unsigned loaded = 0;
    std::error_code ec;
    std::filesystem::directory_iterator entry(path, ec), end;
    while (!ec && entry != end) {
        if (entry->is_regular_file(ec) && !ec) {
            FILE* file = fopen(entry->path().string().c_str(), "rb");
            if (file) {
                X509* cert = PEM_read_X509(file, nullptr, nullptr, nullptr);
                fclose(file);
                if (cert) {
                    if (X509_STORE_add_cert(store, cert) == 1) ++loaded;
                    X509_free(cert);
                }
                ERR_clear_error(); // Ignore non-certificate entries / duplicates, never bypass verification.
            }
        }
        entry.increment(ec);
    }
    return loaded;
}

inline CURLcode GXAndroidSystemTrust(CURL*, void* context, void*)
{
    // SSL_CTX_FUNCTION has backend-specific context types. This build uses OpenSSL.
    const curl_version_info_data* info = curl_version_info(CURLVERSION_NOW);
    if (!info || !info->ssl_version || std::strncmp(info->ssl_version, "OpenSSL/", 8) != 0 || !context)
        return CURLE_SSL_CERTPROBLEM;
    try {
        X509_STORE* store = SSL_CTX_get_cert_store(static_cast<SSL_CTX*>(context));
        if (!store) return CURLE_SSL_CERTPROBLEM;
        // Android 14+ Conscrypt roots and the older read-only system location.
        // Read PEMs directly: Android's filename hash scheme is not OpenSSL CAPATH's scheme.
        unsigned loaded = GXLoadSystemCertificateDirectory(store, "/apex/com.android.conscrypt/cacerts");
        loaded += GXLoadSystemCertificateDirectory(store, "/system/etc/security/cacerts");
        return loaded ? CURLE_OK : CURLE_SSL_CACERT_BADFILE;
    } catch (...) {
        return CURLE_OUT_OF_MEMORY;
    }
}
#endif

inline void GXConfigureOnlineTLS(CURL* curl, bool websocket)
{
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);
    curl_easy_setopt(curl, CURLOPT_PROTOCOLS_STR, websocket ? "wss" : "https");
    curl_easy_setopt(curl, CURLOPT_REDIR_PROTOCOLS_STR, "https");
#if defined(__ANDROID__) || defined(GX_TEST_ANDROID_TLS)
    // The cross-build's default CA path is a host path, absent on Android.
    // Clear it and install system trust through OpenSSL, with peer/hostname checks still enabled.
    curl_easy_setopt(curl, CURLOPT_CAINFO, static_cast<const char*>(nullptr));
    curl_easy_setopt(curl, CURLOPT_CAPATH, static_cast<const char*>(nullptr));
    curl_easy_setopt(curl, CURLOPT_SSL_CTX_FUNCTION, GXAndroidSystemTrust);
#endif
}
