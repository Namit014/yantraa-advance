# Deploying vLLM to the GPU Server

Follow these instructions to deploy the vLLM server on the Ubuntu GPU instance.

## 1. Environment Setup

1. SSH into the GPU server.
2. Create a virtual environment and install vLLM:
   ```bash
   python3 -m venv ~/vllm-env
   source ~/vllm-env/bin/activate
   pip install vllm
   ```

## 2. Deploy Service Files

1. Copy the systemd service and script to the server (assuming the repo is cloned in `~/yantraa-advance`):
   ```bash
   sudo cp ~/yantraa-advance/devops/vllm.service /etc/systemd/system/
   chmod +x ~/yantraa-advance/devops/wait-for-vllm.sh
   ```

## 3. Start the Service

1. Reload systemd to recognize the new service:
   ```bash
   sudo systemctl daemon-reload
   ```
2. Enable the service to start on boot:
   ```bash
   sudo systemctl enable vllm
   ```
3. Start the service:
   ```bash
   sudo systemctl start vllm
   ```

## 4. Verification

1. Check the service status:
   ```bash
   sudo systemctl status vllm
   ```
2. Follow the logs to watch the model loading:
   ```bash
   journalctl -u vllm -f
   ```
3. Manually test the API:
   ```bash
   curl http://localhost:8000/v1/models
   ```
