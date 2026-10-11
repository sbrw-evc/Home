storage "file" {
  path = "/openbao/file"
}

# TLS выключен: порт открыт только на 127.0.0.1 и во внутренней docker-сети.
# Если публикуете OpenBao наружу — только через HTTPS (например, через NPM).
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true
}

api_addr = "http://openbao:8200"
ui       = true

# в непривилегированном LXC mlock обычно недоступен
disable_mlock = true
