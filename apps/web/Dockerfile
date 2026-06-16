# Task 126 + GAPS.md P4-7: build context is the monorepo root voor
# pariteit met de API + worker images. ``next.config.ts`` zet
# ``output: "standalone"`` zodat de builder een gesnoeide
# server-bundle in ``.next/standalone`` legt. De runner kopieert
# daaruit i.p.v. de volledige ``node_modules`` mee te slepen,
# en verkleint het image met ~300 MB.

FROM node:22-alpine AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi


FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ ./
RUN npm run build


FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
# §CB.3 audit-correctie 2026-06-16: non-root runtime user. Alpine
# heeft ``addgroup`` + ``adduser`` ipv groupadd/useradd.
RUN addgroup -S -g 1000 appgroup \
    && adduser -S -u 1000 -G appgroup appuser
# Standalone bundle bevat zijn eigen gesnoeide ``node_modules`` +
# ``server.js`` (entry point). ``.next/static`` en ``public`` moeten
# apart worden gekopieerd omdat ``output: "standalone"`` die niet
# in de standalone-tree zet (Next-conventie).
COPY --from=builder --chown=appuser:appgroup /app/.next/standalone ./
COPY --from=builder --chown=appuser:appgroup /app/.next/static ./.next/static
COPY --from=builder --chown=appuser:appgroup /app/public ./public
USER appuser
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
