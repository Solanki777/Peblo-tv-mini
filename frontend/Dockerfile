# Runs the Vite dev server, not a production build. That's a deliberate
# trade-off for this take-home: docker-compose here is a "run the whole
# thing locally, seeded, in one command" dev environment, not a
# production image. A real deploy would build a static bundle
# (`npm run build`) and serve it from nginx or a CDN - see README's
# pipeline section for what that step would look like.
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
