---
layout: post
title: "unity to wasm"
date: 2025-07-16
---

# Running Your Unity Game on the Web with Docker Compose

Here's a quick guide to exporting your Unity game as WebAssembly (Wasm) and setting it up to run on your website using Docker Compose. Let's dive in!

## Step 1: Export Your Unity Game as Wasm

1. **Open Your Project**: Launch Unity and open your existing game project.
2. **Select WebGL Platform**: Go to `File` > `Build Settings`. In the Build Settings window, select WebGL as your platform.
3. **Build the Project**: Click `Build` to generate your game as a WebAssembly build. Unity will create an HTML file, along with `.wasm` and `.data` files in the chosen directory.

## Step 2: Set Up a Web Server with Docker

To serve your WebAssembly files, we'll use Nginx as a simple web server.

1. **Create a Dockerfile**: Place this Dockerfile alongside your build directory.
    ```Dockerfile
    FROM nginx:alpine
    COPY ./Build /usr/share/nginx/html
    EXPOSE 80
    ```

2. **Build the Image**: Run `docker build -t unity-wasm .` in your terminal to create a Docker image.

## Step 3: Use Docker Compose

We'll orchestrate our setup using Docker Compose.

1. **Create a `docker-compose.yml` File**:

    ```yaml
    version: '3'
    services:
      web:
        build: .
        ports:
          - "8080:80"
    ```

2. **Start the Service**: Run `docker-compose up` in your terminal. It will build and launch the Nginx server.

## Step 4: View Your Game

- Open a web browser and go to `http://localhost:8080` to see your game up and running!

## Conclusion

By exporting your Unity game as WebAssembly and using Docker Compose, you've set up a web server that can run your game in a consistent, isolated environment. This makes deployment simple and scalable.

Happy gaming, and feel free to share your experiences!
