FROM node:22-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm

WORKDIR /app

RUN git clone https://github.com/outsourc-e/hermes-workspace.git . \
    && rm -rf .git

RUN pnpm install --no-frozen-lockfile

RUN pnpm build

ENV NODE_ENV=production
ENV HERMES_API_URL=http://hermes-agent:8642

EXPOSE 3000

CMD ["node", "server-entry.js"]
