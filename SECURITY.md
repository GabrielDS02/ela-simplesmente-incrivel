# Política de Segurança

## Versões com suporte

| Versão | Suporte |
| --- | --- |
| 1.x | ✅ |

## Como reportar uma vulnerabilidade

Por favor, **não** abra uma issue pública. Use o
[reporte privado de vulnerabilidades do GitHub](https://github.com/GabrielDS02/ela-simplesmente-incrivel/security/advisories/new).

Diga o que encontrou e como reproduzir. A resposta vem em até 7 dias.

## Sobre o site

- É 100% estático: não há servidor, banco de dados, formulário ou login.
- Nenhum dado de quem visita é coletado. Os botões finais só abrem o WhatsApp com uma mensagem pronta.
- O Netlify aplica cabeçalhos de segurança (CSP, HSTS, X-Frame-Options e outros), definidos no `netlify.toml`.
