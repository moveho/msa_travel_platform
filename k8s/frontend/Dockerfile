FROM nginx:alpine

# Copy Nginx Config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy Static Files
COPY public /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
