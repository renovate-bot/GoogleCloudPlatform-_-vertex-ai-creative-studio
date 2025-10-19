import { LitElement, css, html } from "https://esm.sh/lit";
import 'https://esm.sh/@material/mwc-button';

class SelfieCamera extends LitElement {
  static styles = css`
    :host {
      display: block;
      border: 1px solid var(--mesop-outline-variant-color);
      border-radius: 12px;
      overflow: hidden;
      position: relative;
      width: 400px;
      height: 300px;
    }
    video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .controls {
      position: absolute;
      bottom: 10px;
      left: 50%;
      transform: translateX(-50%);
    }
  `;

  static get properties() {
    return {
      capture: { type: String },
    };
  }

  constructor() {
    super();
    this.capture = "";
  }

  firstUpdated() {
    this.videoElement = this.shadowRoot.querySelector("video");
    this.canvasElement = this.shadowRoot.querySelector("canvas");
    this.startCamera();
  }

  async startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      this.videoElement.srcObject = stream;
    } catch (err) {
      console.error("Error accessing camera:", err);
    }
  }

  takePicture() {
    console.log("Taking picture...");
    const video = this.videoElement;
    const canvas = this.canvasElement;
    const context = canvas.getContext("2d");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    const dataUrl = canvas.toDataURL("image/png");

    if (this.capture) {
      console.log("Dispatching capture event...");
      this.dispatchEvent(new MesopEvent(this.capture, { value: dataUrl }));
    } else {
      console.error("Capture event handler not set.");
    }
  }

  render() {
    return html`
      <video autoplay playsinline></video>
      <canvas style="display:none;"></canvas>
      <div class="controls">
        <mwc-button raised label="Take Picture" @click=${this.takePicture}></mwc-button>
      </div>
    `;
  }
}

customElements.define("selfie-camera", SelfieCamera);