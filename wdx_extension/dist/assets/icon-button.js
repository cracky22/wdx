import{d as z,i as m,b as I,x as u,c as b,_ as l,t as k,r as R,n as h,f as C,E as p,a as L,m as E}from"./element-internals.js";/**
 * @license
 * Copyright 2021 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function H(t){return(e,o)=>{const{slot:s,selector:n}=t??{},i="slot"+(s?`[name=${s}]`:":not([name])");return z(e,o,{get(){var v;const r=(v=this.renderRoot)==null?void 0:v.querySelector(i),c=(r==null?void 0:r.assignedElements(t))??[];return n===void 0?c:c.filter(d=>d.matches(n))}})}}/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */function B(t){t.addInitializer(e=>{const o=e;o.addEventListener("click",async s=>{const{type:n,[m]:i}=o,{form:r}=i;if(!(!r||n==="button")&&(await new Promise(c=>{setTimeout(c)}),!s.defaultPrevented)){if(n==="reset"){r.reset();return}r.addEventListener("submit",c=>{Object.defineProperty(c,"submitter",{configurable:!0,enumerable:!0,get:()=>o})},{capture:!0,once:!0}),i.setFormValue(o.value),r.requestSubmit()}})})}/**
 * @license
 * Copyright 2022 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */class A extends I{render(){return u`<slot></slot>`}connectedCallback(){if(super.connectedCallback(),this.getAttribute("aria-hidden")==="false"){this.removeAttribute("aria-hidden");return}this.setAttribute("aria-hidden","true")}}/**
 * @license
 * Copyright 2024 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */const P=b`:host{font-size:var(--md-icon-size, 24px);width:var(--md-icon-size, 24px);height:var(--md-icon-size, 24px);color:inherit;font-variation-settings:inherit;font-weight:400;font-family:var(--md-icon-font, Material Symbols Outlined);display:inline-flex;font-style:normal;place-items:center;place-content:center;line-height:1;overflow:hidden;letter-spacing:normal;text-transform:none;user-select:none;white-space:nowrap;word-wrap:normal;flex-shrink:0;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;-moz-osx-font-smoothing:grayscale}::slotted(svg){fill:currentColor}::slotted(*){height:100%;width:100%}
`;/**
 * @license
 * Copyright 2022 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */let f=class extends A{};f.styles=[P];f=l([k("md-icon")],f);/**
 * @license
 * Copyright 2020 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const S=Symbol.for(""),M=t=>{if((t==null?void 0:t.r)===S)return t==null?void 0:t._$litStatic$},x=(t,...e)=>({_$litStatic$:e.reduce((o,s,n)=>o+(i=>{if(i._$litStatic$!==void 0)return i._$litStatic$;throw Error(`Value passed to 'literal' function must be a 'literal' result: ${i}. Use 'unsafeStatic' to pass non-literal values, but
            take care to ensure page security.`)})(s)+t[n+1],t[0]),r:S}),$=new Map,T=t=>(e,...o)=>{const s=o.length;let n,i;const r=[],c=[];let v,d=0,g=!1;for(;d<s;){for(v=e[d];d<s&&(i=o[d],(n=M(i))!==void 0);)v+=n+e[++d],g=!0;d!==s&&c.push(i),r.push(v),d++}if(d===s&&r.push(e[s]),g){const _=r.join("$$lit$$");(e=$.get(_))===void 0&&(r.raw=r,$.set(_,e=r)),o=c}return t(e,...o)},F=T(u);/**
 * @license
 * Copyright 2022 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */function w(t,e=!0){return e&&getComputedStyle(t).getPropertyValue("direction").trim()==="rtl"}/**
 * @license
 * Copyright 2018 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */const V=E(I);class a extends V{constructor(){super(...arguments),this.disabled=!1,this.flipIconInRtl=!1,this.href="",this.target="",this.ariaLabelSelected="",this.toggle=!1,this.selected=!1,this.type="submit",this.value="",this.flipIcon=w(this,this.flipIconInRtl)}get name(){return this.getAttribute("name")??""}set name(e){this.setAttribute("name",e)}get form(){return this[m].form}get labels(){return this[m].labels}willUpdate(){this.href&&(this.disabled=!1)}render(){const e=this.href?x`div`:x`button`,{ariaLabel:o,ariaHasPopup:s,ariaExpanded:n}=this,i=o&&this.ariaLabelSelected,r=this.toggle?this.selected:p;let c=p;return this.href||(c=i&&this.selected?this.ariaLabelSelected:o),F`<${e}
        class="icon-button ${L(this.getRenderClasses())}"
        id="button"
        aria-label="${c||p}"
        aria-haspopup="${!this.href&&s||p}"
        aria-expanded="${!this.href&&n||p}"
        aria-pressed="${r}"
        ?disabled="${!this.href&&this.disabled}"
        @click="${this.handleClick}">
        ${this.renderFocusRing()}
        ${this.renderRipple()}
        ${this.selected?p:this.renderIcon()}
        ${this.selected?this.renderSelectedIcon():p}
        ${this.renderTouchTarget()}
        ${this.href&&this.renderLink()}
  </${e}>`}renderLink(){const{ariaLabel:e}=this;return u`
      <a
        class="link"
        id="link"
        href="${this.href}"
        target="${this.target||p}"
        aria-label="${e||p}"></a>
    `}getRenderClasses(){return{"flip-icon":this.flipIcon,selected:this.toggle&&this.selected}}renderIcon(){return u`<span class="icon"><slot></slot></span>`}renderSelectedIcon(){return u`<span class="icon icon--selected"
      ><slot name="selected"><slot></slot></slot
    ></span>`}renderTouchTarget(){return u`<span class="touch"></span>`}renderFocusRing(){return u`<md-focus-ring
      part="focus-ring"
      for=${this.href?"link":"button"}></md-focus-ring>`}renderRipple(){return u`<md-ripple
      for=${this.href?"link":p}
      ?disabled="${!this.href&&this.disabled}"></md-ripple>`}connectedCallback(){this.flipIcon=w(this,this.flipIconInRtl),super.connectedCallback()}async handleClick(e){await 0,!(!this.toggle||this.disabled||e.defaultPrevented)&&(this.selected=!this.selected,this.dispatchEvent(new InputEvent("input",{bubbles:!0,composed:!0})),this.dispatchEvent(new Event("change",{bubbles:!0})))}}R(a),B(a);a.formAssociated=!0;a.shadowRootOptions={mode:"open",delegatesFocus:!0};l([h({type:Boolean,reflect:!0})],a.prototype,"disabled",void 0);l([h({type:Boolean,attribute:"flip-icon-in-rtl"})],a.prototype,"flipIconInRtl",void 0);l([h()],a.prototype,"href",void 0);l([h()],a.prototype,"target",void 0);l([h({attribute:"aria-label-selected"})],a.prototype,"ariaLabelSelected",void 0);l([h({type:Boolean})],a.prototype,"toggle",void 0);l([h({type:Boolean,reflect:!0})],a.prototype,"selected",void 0);l([h()],a.prototype,"type",void 0);l([h({reflect:!0})],a.prototype,"value",void 0);l([C()],a.prototype,"flipIcon",void 0);/**
 * @license
 * Copyright 2024 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */const O=b`:host{display:inline-flex;outline:none;-webkit-tap-highlight-color:rgba(0,0,0,0);height:var(--_container-height);width:var(--_container-width);justify-content:center}:host([touch-target=wrapper]){margin:max(0px,(48px - var(--_container-height))/2) max(0px,(48px - var(--_container-width))/2)}md-focus-ring{--md-focus-ring-shape-start-start: var(--_container-shape-start-start);--md-focus-ring-shape-start-end: var(--_container-shape-start-end);--md-focus-ring-shape-end-end: var(--_container-shape-end-end);--md-focus-ring-shape-end-start: var(--_container-shape-end-start)}:host([disabled]){pointer-events:none}.icon-button{place-items:center;background:none;border:none;box-sizing:border-box;cursor:pointer;display:flex;place-content:center;outline:none;padding:0;position:relative;text-decoration:none;user-select:none;z-index:0;flex:1;border-start-start-radius:var(--_container-shape-start-start);border-start-end-radius:var(--_container-shape-start-end);border-end-start-radius:var(--_container-shape-end-start);border-end-end-radius:var(--_container-shape-end-end)}.icon ::slotted(*){font-size:var(--_icon-size);height:var(--_icon-size);width:var(--_icon-size);font-weight:inherit}md-ripple{z-index:-1;border-start-start-radius:var(--_container-shape-start-start);border-start-end-radius:var(--_container-shape-start-end);border-end-start-radius:var(--_container-shape-end-start);border-end-end-radius:var(--_container-shape-end-end)}.flip-icon .icon{transform:scaleX(-1)}.icon{display:inline-flex}.link{height:100%;outline:none;position:absolute;width:100%}.touch{position:absolute;height:max(48px,100%);width:max(48px,100%)}:host([touch-target=none]) .touch{display:none}@media(forced-colors: active){:host([disabled]){--_disabled-icon-opacity: 1}}
`;/**
 * @license
 * Copyright 2024 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */const j=b`:host{--_disabled-icon-color: var(--md-icon-button-disabled-icon-color, var(--md-sys-color-on-surface, #1d1b20));--_disabled-icon-opacity: var(--md-icon-button-disabled-icon-opacity, 0.38);--_icon-size: var(--md-icon-button-icon-size, 24px);--_selected-focus-icon-color: var(--md-icon-button-selected-focus-icon-color, var(--md-sys-color-primary, #6750a4));--_selected-hover-icon-color: var(--md-icon-button-selected-hover-icon-color, var(--md-sys-color-primary, #6750a4));--_selected-hover-state-layer-color: var(--md-icon-button-selected-hover-state-layer-color, var(--md-sys-color-primary, #6750a4));--_selected-hover-state-layer-opacity: var(--md-icon-button-selected-hover-state-layer-opacity, 0.08);--_selected-icon-color: var(--md-icon-button-selected-icon-color, var(--md-sys-color-primary, #6750a4));--_selected-pressed-icon-color: var(--md-icon-button-selected-pressed-icon-color, var(--md-sys-color-primary, #6750a4));--_selected-pressed-state-layer-color: var(--md-icon-button-selected-pressed-state-layer-color, var(--md-sys-color-primary, #6750a4));--_selected-pressed-state-layer-opacity: var(--md-icon-button-selected-pressed-state-layer-opacity, 0.12);--_state-layer-height: var(--md-icon-button-state-layer-height, 40px);--_state-layer-shape: var(--md-icon-button-state-layer-shape, var(--md-sys-shape-corner-full, 9999px));--_state-layer-width: var(--md-icon-button-state-layer-width, 40px);--_focus-icon-color: var(--md-icon-button-focus-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-icon-color: var(--md-icon-button-hover-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-state-layer-color: var(--md-icon-button-hover-state-layer-color, var(--md-sys-color-on-surface-variant, #49454f));--_hover-state-layer-opacity: var(--md-icon-button-hover-state-layer-opacity, 0.08);--_icon-color: var(--md-icon-button-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_pressed-icon-color: var(--md-icon-button-pressed-icon-color, var(--md-sys-color-on-surface-variant, #49454f));--_pressed-state-layer-color: var(--md-icon-button-pressed-state-layer-color, var(--md-sys-color-on-surface-variant, #49454f));--_pressed-state-layer-opacity: var(--md-icon-button-pressed-state-layer-opacity, 0.12);--_container-shape-start-start: 0;--_container-shape-start-end: 0;--_container-shape-end-end: 0;--_container-shape-end-start: 0;--_container-height: 0;--_container-width: 0;height:var(--_state-layer-height);width:var(--_state-layer-width)}:host([touch-target=wrapper]){margin:max(0px,(48px - var(--_state-layer-height))/2) max(0px,(48px - var(--_state-layer-width))/2)}md-focus-ring{--md-focus-ring-shape-start-start: var(--_state-layer-shape);--md-focus-ring-shape-start-end: var(--_state-layer-shape);--md-focus-ring-shape-end-end: var(--_state-layer-shape);--md-focus-ring-shape-end-start: var(--_state-layer-shape)}.standard{background-color:rgba(0,0,0,0);color:var(--_icon-color);--md-ripple-hover-color: var(--_hover-state-layer-color);--md-ripple-hover-opacity: var(--_hover-state-layer-opacity);--md-ripple-pressed-color: var(--_pressed-state-layer-color);--md-ripple-pressed-opacity: var(--_pressed-state-layer-opacity)}.standard:hover{color:var(--_hover-icon-color)}.standard:focus{color:var(--_focus-icon-color)}.standard:active{color:var(--_pressed-icon-color)}.standard:disabled{color:var(--_disabled-icon-color)}md-ripple{border-radius:var(--_state-layer-shape)}.standard:disabled .icon{opacity:var(--_disabled-icon-opacity)}.selected{--md-ripple-hover-color: var(--_selected-hover-state-layer-color);--md-ripple-hover-opacity: var(--_selected-hover-state-layer-opacity);--md-ripple-pressed-color: var(--_selected-pressed-state-layer-color);--md-ripple-pressed-opacity: var(--_selected-pressed-state-layer-opacity)}.selected:not(:disabled){color:var(--_selected-icon-color)}.selected:not(:disabled):hover{color:var(--_selected-hover-icon-color)}.selected:not(:disabled):focus{color:var(--_selected-focus-icon-color)}.selected:not(:disabled):active{color:var(--_selected-pressed-icon-color)}
`;/**
 * @license
 * Copyright 2021 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */let y=class extends a{getRenderClasses(){return{...super.getRenderClasses(),standard:!0}}};y.styles=[O,j];y=l([k("md-icon-button")],y);export{x as i,H as o,B as s,F as u};
