# Политика для дашборда: только свои секреты
path "secret/data/npm-dashboard/*" {
  capabilities = ["create", "read", "update"]
}

path "secret/metadata/npm-dashboard/*" {
  capabilities = ["delete"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}
