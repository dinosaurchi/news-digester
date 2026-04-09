FROM ghcr.io/anomalyco/opencode:latest

RUN apk add --no-cache nodejs npm

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev

COPY src ./src

ENTRYPOINT []
EXPOSE 8080
CMD ["npm", "run", "start"]
