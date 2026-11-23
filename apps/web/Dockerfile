FROM node:22-alpine AS build
WORKDIR /srv
COPY packages/shared /srv/packages/shared
COPY apps/web /srv/apps/web
WORKDIR /srv/apps/web
RUN npm ci && npm run build

FROM nginx:1.27-alpine
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /srv/apps/web/dist /usr/share/nginx/html
EXPOSE 80
