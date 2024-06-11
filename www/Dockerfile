# Use an updated Node.js runtime as a parent image
FROM node:18-alpine as builder

WORKDIR /app

# Copy the package.json and yarn.lock files
COPY . .

# Install dependencies
RUN yarn install --frozen-lockfile

# Build the project
RUN yarn build

# Stage 2: Serve the app using a production-ready Node image
FROM node:18-alpine

WORKDIR /app

# Copy the build output from the builder stage
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json

# Expose the port the app runs on
EXPOSE 3000

# Start the app
CMD ["yarn", "start"]