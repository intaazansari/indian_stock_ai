# ──────────────────────────────────────────────
# Frontend Dockerfile
# Multi-stage: development + production targets
# ──────────────────────────────────────────────

# ── Base ───────────────────────────────────────
FROM node:20-alpine AS base

WORKDIR /app
RUN apk add --no-cache libc6-compat

# ── Dependencies ───────────────────────────────
FROM base AS deps

COPY package.json package-lock.json* ./
RUN npm ci

# ── Development ────────────────────────────────
FROM base AS development

COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
ENV PORT=3000
CMD ["npm", "run", "dev"]

# ── Builder ────────────────────────────────────
FROM base AS builder

COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1

# NEXT_PUBLIC_API_URL must be baked in at build time (Next.js requirement).
# Render passes this as a build-time env var from render.yaml.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# ── Production ─────────────────────────────────
FROM base AS production

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# PORT is injected by Render
ENV PORT=10000
ENV HOSTNAME="0.0.0.0"
EXPOSE $PORT

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget -qO- http://localhost:${PORT}/ || exit 1

CMD ["node", "server.js"]
