import { LitElement, css, html } from "https://esm.sh/lit";

class MediaDetailViewer extends LitElement {
  static styles = css`
    :host {
      display: block;
      width: 100%;
    }
    .container {
      display: flex;
      flex-direction: row;
      gap: 24px;
    }
    .left-column {
      flex: 3;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .right-column {
      flex: 2;
      display: flex;
      flex-direction: column;
      gap: 16px;
      max-height: 80vh; /* Allow metadata to scroll */
      overflow-y: auto;
    }
    .main-asset {
      position: relative; /* For carousel buttons */
    }
    .main-asset img,
    .main-asset video {
      width: 100%;
      max-height: 60vh;
      object-fit: contain;
      border-radius: 8px;
    }
    .carousel-btn {
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      background-color: rgba(0, 0, 0, 0.5);
      color: white;
      border: none;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      cursor: pointer;
      font-size: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .carousel-btn:hover {
      background-color: rgba(0, 0, 0, 0.8);
    }
    .prev-btn {
      left: 10px;
    }
    .next-btn {
      right: 10px;
    }
    .source-images {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .source-images img {
      width: 100px;
      height: 100px;
      object-fit: cover;
      border-radius: 4px;
      border: 1px solid var(--mesop-outline-variant-color);
    }
    h3 {
      margin: 0 0 8px 0;
      font-size: 1.2rem;
      font-weight: 500;
    }
    .metadata-item {
      display: flex;
      flex-direction: column;
      margin-bottom: 8px;
    }
    .metadata-key {
      font-weight: bold;
      font-size: 0.9rem;
      color: var(--mesop-on-surface-variant-color);
    }
    .metadata-value {
      font-size: 1rem;
      white-space: pre-wrap;
      word-wrap: break-word;
    }
  `;

  static get properties() {
    return {
      mediaType: { type: String },
      primaryUrlsJson: { type: String },
      sourceUrlsJson: { type: String },
      metadataJson: { type: String },
      _currentIndex: { state: true },
    };
  }

  constructor() {
    super();
    this.mediaType = "";
    this.primaryUrlsJson = "[]";
    this.sourceUrlsJson = "[]";
    this.metadataJson = "{}";
    this._currentIndex = 0;
  }

  _navigate(direction) {
    const urls = JSON.parse(this.primaryUrlsJson);
    const newIndex = this._currentIndex + direction;
    if (newIndex >= 0 && newIndex < urls.length) {
      this._currentIndex = newIndex;
    }
  }

  renderPrimaryAsset() {
    const urls = JSON.parse(this.primaryUrlsJson);
    if (urls.length === 0) return html``;

    const currentUrl = urls[this._currentIndex];

    let assetHtml;
    switch (this.mediaType) {
      case "image":
        assetHtml = html`<img .src=${currentUrl} />`;
        break;
      case "video":
        assetHtml = html`<video .src=${currentUrl} controls autoplay></video>`;
        break;
      case "audio":
        assetHtml = html`<audio .src=${currentUrl} controls autoplay></audio>`;
        break;
      default:
        assetHtml = html`<p>Unknown or unsupported media type.</p>`;
    }

    const showButtons = urls.length > 1;

    return html`
      ${assetHtml}
      ${showButtons
        ? html`
            <button
              class="carousel-btn prev-btn"
              @click=${() => this._navigate(-1)}
              ?disabled=${this._currentIndex === 0}
            >
              &#x2039;
            </button>
            <button
              class="carousel-btn next-btn"
              @click=${() => this._navigate(1)}
              ?disabled=${this._currentIndex === urls.length - 1}
            >
              &#x203A;
            </button>
          `
        : ""}
    `;
  }

  renderSourceImages() {
    try {
      const sourceUrls = JSON.parse(this.sourceUrlsJson);
      if (sourceUrls.length === 0) return html``;

      return html`
        <h3>Source Images</h3>
        <div class="source-images">
          ${sourceUrls.map((url) => html`<img .src=${url} />`)}
        </div>
      `;
    } catch (e) {
      return html``;
    }
  }

  renderMetadata() {
    try {
      const metadata = JSON.parse(this.metadataJson);
      return Object.entries(metadata).map(
        ([key, value]) =>
          html`
            <div class="metadata-item">
              <span class="metadata-key">${key}</span>
              <span class="metadata-value">${value}</span>
            </div>
          `
      );
    } catch (e) {
      return html`<p>Could not parse metadata.</p>`;
    }
  }

  render() {
    return html`
      <div class="container">
        <div class="left-column">
          <div class="main-asset">${this.renderPrimaryAsset()}</div>
          ${this.renderSourceImages()}
        </div>
        <div class="right-column">
          <h3>Metadata</h3>
          ${this.renderMetadata()}
        </div>
      </div>
    `;
  }
}

customElements.define("media-detail-viewer", MediaDetailViewer);
