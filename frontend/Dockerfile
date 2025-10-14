FROM node:18 AS build
WORKDIR /app
ARG VITE_API_BASE_URL=http://localhost:5000
COPY package*.json ./
RUN npm install
COPY . .
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
