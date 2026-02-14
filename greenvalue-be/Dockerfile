# ============================================================
# GreenValue AI Backend - Production Dockerfile (Multi-Stage)
# ============================================================
# Layer 3: NestJS Modular Monolith (Port: 3000)
# - Fastify Adapter
# - Prisma ORM + PostgreSQL + PostGIS
# - gRPC Client (AI Engine connection)
# - BullMQ (Redis queues)
# - Socket.IO (Real-time events)
# ============================================================

# --- Stage 1: Builder (Install & Compile) ---
FROM node:20-alpine AS builder

WORKDIR /build

# Install build dependencies for native modules (bcrypt) + openssl for Prisma
RUN apk add --no-cache python3 make g++ openssl

# Copy package files + prisma schema (postinstall runs prisma generate)
COPY package.json package-lock.json* ./
COPY prisma ./prisma

# Install deps (postinstall will run prisma generate automatically)
RUN npm ci

# Copy source code and build
COPY . .
RUN npm run build

# Save Prisma generated client before prune (prune removes it)
RUN cp -r node_modules/.prisma /tmp/.prisma && \
    cp -r node_modules/@prisma /tmp/@prisma

# Prune dev dependencies
RUN npm prune --production

# Restore Prisma client after prune
RUN cp -r /tmp/.prisma node_modules/.prisma && \
    cp -r /tmp/@prisma node_modules/@prisma

# --- Stage 2: Runtime (Minimal Production Image) ---
FROM node:20-alpine AS runtime

WORKDIR /app

# Install runtime native libs + openssl for Prisma engine
RUN apk add --no-cache vips libstdc++ curl wget openssl

# Copy production node_modules from builder
COPY --from=builder /build/node_modules ./node_modules

# Copy Prisma schema + generated client
COPY --from=builder /build/prisma ./prisma
COPY --from=builder /build/node_modules/.prisma ./node_modules/.prisma

# Copy compiled application
COPY --from=builder /build/dist ./dist

# Copy package.json (needed for metadata)
COPY --from=builder /build/package.json ./

# Copy proto files for gRPC
COPY proto ./proto

# Create non-root user
RUN addgroup -S greenvalue && \
    adduser -S -G greenvalue greenvalue && \
    mkdir -p /app/uploads /app/logs && \
    chown -R greenvalue:greenvalue /app

USER greenvalue

# Environment
ENV NODE_ENV=production \
    PORT=3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health/live || exit 1

EXPOSE 3000

# Start with node (not npx/nest) for production
CMD ["node", "dist/main.js"]
