FROM node:20-slim

WORKDIR /app

# Install deps first so the layer caches across code changes.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# NEXT_PUBLIC_* values are inlined at build time, so this has to be a
# build arg rather than only a runtime env var. It points at the backend
# as reached from your *browser*, not from inside the container network.
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE

RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
