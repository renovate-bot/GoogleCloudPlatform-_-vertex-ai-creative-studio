import { LitElement, css, html } from 'https://esm.sh/lit';
import { styleMap } from 'https://esm.sh/lit/directives/style-map.js';

class InteractiveTile extends LitElement {
  // -- Define properties received from Python --
  static properties = {
    label: { type: String },
    icon: { type: String },
    description: { type: String },
    route: { type: String },
    videoUrl: { type: String },
    tileClickEvent: { type: String },
    isHovered: { state: true },
  };

  constructor() {
    super();
    this.label = '';
    this.icon = '';
    this.description = '';
    this.route = '';
    this.videoUrl = '';
    this.tileClickEvent = '';
    this.isHovered = false;
  }

  // -- Event Handlers --
  handleMouseOver() { this.isHovered = true; }
  handleMouseOut() { this.isHovered = false; }
  handleClick() {
    if (!this.tileClickEvent) {
      console.error('Mesop event handler ID for tileClickEvent is not set.');
      return;
    }
    this.dispatchEvent(new MesopEvent(this.tileClickEvent, { route: this.route }));
  }

  // -- SVG Icon Renderer --
  renderIcon() {
    const iconStyle = `width: 48px; height: 48px; fill: currentColor;`;
    switch (this.icon) {
      case 'image':
        return html`<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24"><path d="M0 0h24v24H0z" fill="none"/><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>`;
      case 'edit':
        return html`<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px"><path d="M0 0h24v24H0z" fill="none"/><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>`;
      case 'movie_filter':
        return html`<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px"><path d="M0 0h24v24H0V0z" fill="none"/><path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/></svg>`;
      case 'spark':
        return html `<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#4285f4ff"><path d="M480-80q-6 0-11-4t-7-10q-17-67-51-126t-83-108q-49-49-108-83T94-462q-6-2-10-7t-4-11q0-6 4-11t10-7q67-17 126-51t108-83q49-49 83-108t51-126q2-6 7-10t11-4q6 0 10.5 4t6.5 10q18 67 52 126t83 108q49 49 108 83t126 51q6 2 10 7t4 11q0 6-4 11t-10 7q-67 17-126 51t-108 83q-49 49-83 108T498-94q-2 6-7 10t-11 4Z"/></svg>`
      case 'record_voice_over':
        return html`<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24"><path d="M0 0h24v24H0z" fill="none"/><path d="M9 11.75c-.69 0-1.25.56-1.25 1.25s.56 1.25 1.25 1.25 1.25-.56 1.25-1.25-.56-1.25-1.25-1.25zm6 0c-.69 0-1.25.56-1.25 1.25s.56 1.25 1.25 1.25 1.25-.56 1.25-1.25-.56-1.25-1.25-1.25zM12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm0-14c-2.33 0-4.31 1.46-5.11 3.5h10.22c-.8-2.04-2.78-3.5-5.11-3.5z"/></svg>`;
      case 'graphic_eq':
        return html `<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px" fill="#5f6368"><path d="M0 0h24v24H0V0z" fill="none"/><path d="M7 18h2V6H7v12zm4 4h2V2h-2v20zm-8-8h2v-4H3v4zm12 4h2V6h-2v12zm4-8v4h2v-4h-2z"/></svg>`
      case 'music_note':
        return html`<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24"><path d="M0 0h24v24H0z" fill="none"/><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>`;
      case 'shopping_bag':
        return html`<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24"><path d="M0 0h24v24H0z" fill="none"/><path d="M18 6h-2c0-2.21-1.79-4-4-4S8 3.79 8 6H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-6-2c1.1 0 2 .9 2 2h-4c0-1.1.9-2 2-2zm6 16H6V8h2v2c0 .55.45 1 1 1s1-.45 1-1V8h4v2c0 .55.45 1 1 1s1-.45 1-1V8h2v12z"/></svg>`;
      case 'perm_media': // Filled version
        return html`<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px"><path d="M0 0h24v24H0z" fill="none"/><path d="M22 16V4c0-1.1-.9-2-2-2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2zm-11-4l2.03 2.71L16 11l4 5H8l3-4zM2 6v14c0 1.1.9 2 2 2h14v-2H4V6H2z"/></svg>`;
      case 'info':
        return html`<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px"><path d="M0 0h24v24H0z" fill="none"/><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>`;
      case 'settings':
        return html`<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px"><path d="M0 0h24v24H0z" fill="none"/><path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18-.49.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/></svg>`;
      case 'checkroom':
        return html `<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" enable-background="new 0 0 24 24" height="24px" viewBox="0 0 24 24" width="24px" fill="#5f6368"><g><rect fill="none" height="24" width="24"/><path d="M21.6,18.2L13,11.75v-0.91c1.65-0.49,2.8-2.17,2.43-4.05c-0.26-1.31-1.3-2.4-2.61-2.7C10.54,3.57,8.5,5.3,8.5,7.5h2 C10.5,6.67,11.17,6,12,6s1.5,0.67,1.5,1.5c0,0.84-0.69,1.52-1.53,1.5C11.43,8.99,11,9.45,11,9.99v1.76L2.4,18.2 C1.63,18.78,2.04,20,3,20h9h9C21.96,20,22.37,18.78,21.6,18.2z M6,18l6-4.5l6,4.5H6z"/></g></svg>`
      case 'style':
        return html `<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#4285f4ff"><path d="m159-168-34-14q-31-13-41.5-45t3.5-63l72-156v278Zm160 88q-33 0-56.5-23.5T239-160v-240l106 294q3 7 6 13.5t8 12.5h-40Zm206-4q-32 12-62-3t-42-47L243-622q-12-32 2-62.5t46-41.5l302-110q32-12 62 3t42 47l178 488q12 32-2 62.5T827-194L525-84Zm-86-476q17 0 28.5-11.5T479-600q0-17-11.5-28.5T439-640q-17 0-28.5 11.5T399-600q0 17 11.5 28.5T439-560Zm58 400 302-110-178-490-302 110 178 490ZM319-650l302-110-302 110Z"/></svg>`
      case 'scene':
        return html `<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#4285f4ff"><path d="M800-80v-600q0-33-23.5-56.5T720-760h-40v52q0 12-8 20t-20 8H428q-14 0-22.5-15t-1.5-29l76-164q7-15 20.5-23.5T532-920h92q24 0 40 18t16 42v20h40q66 0 113 47t47 113v600h-80ZM508-760h92v-80h-56l-36 80ZM200-80q-51 0-85.5-34.5T80-200v-100q0-33 22-61.5t58-34.5v-84q0-33 23.5-56.5T240-560h320q33 0 56.5 23.5T640-480v84q36 6 58 33t22 63v100q0 51-34.5 85.5T600-80H200Zm40-400v100q18 15 29 35.5t11 44.5v20h240v-20q0-24 11-44.5t29-35.5v-100H240Zm-40 320h400q18 0 29-12.5t11-27.5v-100q0-9-5.5-14.5T620-320q-9 0-14.5 5.5T600-300v100H200v-100q0-9-5.5-14.5T180-320q-9 0-14.5 5.5T160-300v100q0 15 11 27.5t29 12.5Zm320-120H280h240ZM240-480h320-320Zm-40 320h400-400Z"/></svg>`
      case 'portrait':
        return html`<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24"><path d="M0 0h24v24H0z" fill="none"/><path d="M12 12.25c1.24 0 2.25-1.01 2.25-2.25S13.24 7.75 12 7.75 9.75 8.76 9.75 10s1.01 2.25 2.25 2.25zm4.5 4c0-1.5-3-2.25-4.5-2.25s-4.5.75-4.5 2.25V17h9v-.75zM19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/></svg>`;
      case 'person':
        return html`<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px"><path d="M0 0h24v24H0z" fill="none"/><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>`;
      default:
        // Fallback square icon
        return html`<svg style=${iconStyle} xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px"><path d="M0 0h24v24H0z" fill="none"/><path d="M3 3v18h18V3H3zm16 16H5V5h14v14z"/></svg>`;
    }
  }


  // -- Styles --
  static styles = css`
    :host {
      display: block;
      cursor: pointer;
      font-family: 'Google Sans', 'Helvetica Neue', sans-serif;
    }
    .card {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      width: 160px;
      height: 160px;
      padding: 16px;
      border-radius: 12px;
      border: 1px solid var(--mesop-theme-outline-variant, #ccc);
      transition: all 0.2s ease-in-out;
      box-sizing: border-box;
      background-size: cover;
      background-position: center;
      overflow: hidden; /* Ensures video and overlay don't spill out */
      position: relative; /* For positioning the overlay and video */

      /* Default theme for non-video tiles */
      background-color: var(--mesop-theme-surface-container-low, #f5f5f5);
      color: var(--mesop-theme-on-surface-variant, #444);
    }
    /* Hover effect for non-video tiles */
    .card:not(.has-video):hover {
      background-color: var(--mesop-theme-secondary-container, #e8def8);
      color: var(--mesop-theme-on-secondary-container, #1d192b);
    }
    .icon-container {
      margin-bottom: 12px;
    }
    .label { font-weight: 500; }
    .description { font-size: 0.9em; }
    .hover-label {
      font-weight: bold;
      font-size: 1.1em;
      margin-bottom: 12px;
    }
    .content-container {
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 16px;
      box-sizing: border-box;
      z-index: 2; /* Position content above the background video */
      position: relative;
      /* Ensure overlay corners match the parent card's corners */
      border-radius: 12px;
    }
    .background-video {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      min-width: 100%;
      min-height: 100%;
      width: auto;
      height: auto;
      z-index: 1;
    }
  `;

  // -- Render method --
  render() {
    const hasVideo = this.videoUrl && this.videoUrl.length > 0;

    // Styles for the container that holds the text/icon content.
    // This acts as the overlay for video tiles.
    const contentContainerStyles = {
      backgroundColor: hasVideo ? 'rgba(0, 0, 0, 0.15)' : 'transparent',
      textShadow: hasVideo ? '1px 1px 2px rgba(0,0,0,0.7)' : 'none',
    };

    // Dynamically set the text color on the main card.
    // It will be white for video tiles, and inherit from the CSS for non-video tiles.
    const cardStyles = {
       color: hasVideo ? 'white' : 'inherit',
    }

    return html`
      <div
        class="card ${hasVideo ? 'has-video' : ''}"
        style=${styleMap(cardStyles)}
        @mouseover=${this.handleMouseOver}
        @mouseout=${this.handleMouseOut}
        @click=${this.handleClick}
      >
        ${hasVideo
          ? html`<video class="background-video" autoplay loop muted playsinline .src=${this.videoUrl}></video>`
          : ''
        }

        <div class="content-container" style=${styleMap(contentContainerStyles)}>
          ${this.isHovered
            ? html`
                <div class="hover-label">${this.label}</div>
                <div class="description">${this.description}</div>
              `
            : html`
                <div class="icon-container">${this.renderIcon()}</div>
                <div class="label">${this.label}</div>
              `}
        </div>
      </div>
    `;
  }
}

customElements.define('interactive-tile', InteractiveTile);

