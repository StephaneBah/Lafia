# Image d'une application Lafia, construite depuis l'espace de travail web/ :
#   docker build --build-arg APPLICATION=soin web
# Le système de design est compilé dans l'application ; l'image ne garde que la sortie autonome de Next.js.

FROM node:22-alpine AS construction
ARG APPLICATION
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /web
COPY . .
RUN npm ci && npm run build --workspace "@lafia/${APPLICATION}"

FROM node:22-alpine
ARG APPLICATION
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /application
COPY --from=construction --chown=node:node /web/${APPLICATION}/.next/standalone ./
COPY --from=construction --chown=node:node /web/${APPLICATION}/.next/static ./${APPLICATION}/.next/static
WORKDIR /application/${APPLICATION}
USER node

EXPOSE 3000
# Sain quand le serveur écoute. La page, elle, interroge le service à chaque requête : la sonde ne la charge pas.
HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=10s \
    CMD ["node", "-e", "require('node:net').connect(3000, '127.0.0.1').on('connect', () => process.exit(0)).on('error', () => process.exit(1))"]
CMD ["node", "server.js"]
