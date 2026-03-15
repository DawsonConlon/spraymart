# Simple Docker image to serve the static frontend
FROM nginx:alpine

# Remove the default nginx index file (optional)
RUN rm -f /usr/share/nginx/html/*

# Copy frontend static assets
COPY . /usr/share/nginx/html

# Expose default HTTP port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
