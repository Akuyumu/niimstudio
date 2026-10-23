<script lang="ts">
  import Dropdown from "bootstrap/js/dist/dropdown";
  import * as fabric from "fabric";
  import { onDestroy, onMount, tick } from "svelte";
  import { ArUcoMarker } from "$/fabric-object/aruco";
  import { Barcode } from "$/fabric-object/barcode";
  import { QRCode } from "$/fabric-object/qrcode";
  import { iconCodepoints, type MaterialIcon } from "$/styles/mdi_icons";
  import { appConfig, automation, connectionState, csvData, loadedFonts, printJobActive } from "$/stores";
  import {
    type ExportedLabelTemplate,
    type FabricJson,
    type LabelProps,
    type MoveDirection,
    type OjectType,
  } from "$/types";
  import { FileUtils } from "$/utils/file_utils";
  import { tr } from "$/utils/i18n";
  import { LabelDesignerObjectHelper } from "$/utils/label_designer_object_helper";
  import { LocalStoragePersistence } from "$/utils/persistence";
  import { Toasts } from "$/utils/toasts";
  import { UndoRedo, type UndoState } from "$/utils/undo_redo";
  import BarcodeParamsPanel from "$/components/designer-controls/BarcodeParamsControls.svelte";
  import CsvControl from "$/components/designer-controls/CsvControl.svelte";
  import GenericObjectParamsControls from "$/components/designer-controls/GenericObjectParamsControls.svelte";
  import IconPicker from "$/components/designer-controls/IconPicker.svelte";
  import LabelPropsEditor from "$/components/designer-controls/LabelPropsEditor.svelte";
  import MdIcon from "$/components/basic/MdIcon.svelte";
  import ObjectPicker from "$/components/designer-controls/ObjectPicker.svelte";
  import PrintPreview from "$/components/PrintPreview.svelte";
  import ArUcoParamsPanel from "$/components/designer-controls/ArUcoParamsControls.svelte";
  import QrCodeParamsPanel from "$/components/designer-controls/QRCodeParamsControls.svelte";
  import TextParamsControls from "$/components/designer-controls/TextParamsControls.svelte";
  import VariableInsertControl from "$/components/designer-controls/VariableInsertControl.svelte";
  import { DEFAULT_LABEL_PROPS, GRID_SIZE, OBJECT_DEFAULTS } from "$/defaults";
  import { LabelDesignerUtils } from "$/utils/label_designer_utils";
  import SavedLabelsMenu from "$/components/designer-controls/SavedLabelsMenu.svelte";
  import { CustomCanvas } from "$/fabric-object/custom_canvas";
  import VectorParamsControls from "$/components/designer-controls/VectorParamsControls.svelte";
  import { CanvasUtils } from "$/utils/canvas_utils";
  import { isNative, nativeRequest } from "$/desktop/bridge";
  import { ExportedLabelTemplateSchema } from "$/types";
  import SelectionToolbar from "$/desktop/SelectionToolbar.svelte";
  import CodeEditor, { type CodeContent } from "$/desktop/CodeEditor.svelte";
  import StockSetup from "$/desktop/StockSetup.svelte";
  import { fitZoom } from "$/desktop/zoom";

  let { saveTemplate }: { saveTemplate?: () => void } = $props();

  let htmlCanvas: HTMLCanvasElement;
  let stageColumn = $state<HTMLElement>();
  let canvasViewport = $state<HTMLElement>();

  let fabricCanvas = $state<CustomCanvas>();
  let labelProps = $state<LabelProps>(
    isNative ? { ...DEFAULT_LABEL_PROPS, shape: "rounded_rect" } : DEFAULT_LABEL_PROPS,
  );
  let previewOpened = $state<boolean>(false);
  let selectedObject = $state<fabric.FabricObject | undefined>(undefined);
  let selectedCount = $state<number>(0);
  let editRevision = $state<number>(0);
  let printNow = $state<boolean>(false);
  let csvEnabled = $state<boolean>(false);
  let windowWidth = $state<number>(0);
  let undoState = $state<UndoState>({ undoDisabled: false, redoDisabled: false });
  let zoomText = $state<string>("100%");
  let zoomMode = $state<"fit" | "manual">(isNative ? "fit" : "manual");
  let clippedX = $state(false);
  let clippedY = $state(false);
  let draftTimer: ReturnType<typeof setTimeout> | undefined;
  let draftReady = $state(false);
  let starterCanvas: string | undefined;
  let draftState = $state("Draft saved locally");
  let codeEditor = $state<{ kind: "qrcode" | "barcode"; existing?: QRCode | Barcode }>();

  const saveDraft = () => {
    if (!isNative || !draftReady || !fabricCanvas) return false;
    clearTimeout(draftTimer);
    try {
      // Draft restoration needs the editable data, not an encoded preview image.
      const draft = FileUtils.makeExportedLabel(fabricCanvas, labelProps, csvEnabled, false);
      LocalStoragePersistence.validateAndSaveObject("studio_draft", draft, ExportedLabelTemplateSchema);
      draftState = "Draft saved locally";
      return true;
    } catch (error) {
      draftState = "Draft not saved — export your work";
      console.error(error);
      return false;
    }
  };

  const scheduleDraft = () => {
    if (!isNative || !draftReady) return;
    draftState = "Saving draft…";
    clearTimeout(draftTimer);
    draftTimer = setTimeout(saveDraft, 500);
  };

  const undo = new UndoRedo();

  const discardSelection = () => {
    fabricCanvas!.discardActiveObject();
    fabricCanvas!.requestRenderAll();
    selectedObject = undefined;
    selectedCount = 0;
    editRevision = 0;
  };

  const loadLabelData = async (data: ExportedLabelTemplate) => {
    undo.paused = true;
    onUpdateLabelProps(data.label);
    if (data.csv) {
      $csvData = data.csv;
      csvEnabled = true;
    }
    await FileUtils.loadCanvasState(fabricCanvas!, data.canvas);
    undo.paused = false;
  };

  undo.onLabelUpdate = loadLabelData;
  undo.onStateUpdate = (state: UndoState) => {
    undoState = state;
    scheduleDraft();
  };

  const deleteSelected = () => {
    LabelDesignerUtils.deleteSelection(fabricCanvas!);
    discardSelection();
  };

  const cloneSelected = () => {
    LabelDesignerUtils.cloneSelection(fabricCanvas!).then(() => undo.push(fabricCanvas!, labelProps));
  };

  const moveSelected = (direction: MoveDirection, ctrl?: boolean) => {
    LabelDesignerUtils.moveSelection(fabricCanvas!, direction, ctrl);
    undo.push(fabricCanvas!, labelProps);
  };

  const onKeyDown = (e: KeyboardEvent) => {
    const key: string = e.key.toLowerCase();
    // windows and linux users are used to ctrl, mac users use cmd
    const cmdOrCtrl = e.metaKey || e.ctrlKey;
    if (isNative && cmdOrCtrl && key === "s") {
      e.preventDefault();
      if (!document.querySelector(".modal.show")) saveTemplate?.();
      return;
    }
    if (document.querySelector("dialog[open], .modal.show")) return;

    // Esc
    if (key === "escape") {
      discardSelection();
      return;
    }

    if (LabelDesignerUtils.isAnyInputFocused(fabricCanvas!)) {
      return;
    }

    // Arrows
    if (key.startsWith("arrow")) {
      moveSelected(key.slice("arrow".length) as MoveDirection, cmdOrCtrl);
      return;
    }

    if (e.repeat) {
      return;
    }

    // Ctrl + D
    if (cmdOrCtrl && key === "d") {
      e.preventDefault();
      cloneSelected();
      return;
    }

    // Ctrl + Y, Ctrl + Shift + Z
    if ((cmdOrCtrl && key === "y") || (cmdOrCtrl && e.shiftKey && key === "z")) {
      e.preventDefault();
      if (!undoState.redoDisabled) {
        undo.redo();
      }
      return;
    }

    // Ctrl + Z
    if (cmdOrCtrl && key === "z") {
      e.preventDefault();
      if (!undoState.undoDisabled) {
        undo.undo();
      }
      return;
    }

    // Del
    if (key === "delete" || key === "backspace") {
      deleteSelected();
      return;
    }
  };

  const updateClipState = () => {
    if (!canvasViewport) return;
    clippedX = canvasViewport.scrollWidth > canvasViewport.clientWidth + 1;
    clippedY = canvasViewport.scrollHeight > canvasViewport.clientHeight + 1;
  };

  const fitCanvasToViewport = () => {
    if (!isNative || !fabricCanvas || !stageColumn || !canvasViewport) return;
    zoomMode = "fit";
    requestAnimationFrame(() => {
      if (!fabricCanvas || !stageColumn || !canvasViewport) return;
      const style = getComputedStyle(stageColumn);
      const availableWidth = Math.max(
        1,
        stageColumn.clientWidth -
          Number.parseFloat(style.paddingLeft || "0") -
          Number.parseFloat(style.paddingRight || "0") -
          6,
      );
      const maxHeight = Number.parseFloat(getComputedStyle(canvasViewport).maxHeight);
      const availableHeight = Math.max(1, (Number.isFinite(maxHeight) ? maxHeight : window.innerHeight * 0.54) - 6);
      const zoom = fitZoom(fabricCanvas.getWidth(), fabricCanvas.getHeight(), availableWidth, availableHeight);
      if (zoom === undefined) return;
      fabricCanvas.virtualZoom(zoom, "api");
      canvasViewport.scrollLeft = Math.max(0, (canvasViewport.scrollWidth - canvasViewport.clientWidth) / 2);
      canvasViewport.scrollTop = Math.max(0, (canvasViewport.scrollHeight - canvasViewport.clientHeight) / 2);
      updateClipState();
    });
  };

  const onUpdateLabelProps = (newProps: LabelProps) => {
    const sizeChanged =
      labelProps.size.width !== newProps.size.width || labelProps.size.height !== newProps.size.height;
    labelProps = newProps;
    fabricCanvas!.setDimensions(labelProps.size);
    if (isNative && sizeChanged) {
      zoomMode = "fit";
      requestAnimationFrame(fitCanvasToViewport);
    } else {
      fabricCanvas!.virtualZoom(fabricCanvas!.getVirtualZoom());
    }
    try {
      LocalStoragePersistence.saveLastLabelProps(labelProps);
      undo.push(fabricCanvas!, labelProps);
    } catch (e) {
      Toasts.zodErrors(e, "Label parameters save error:");
    }
  };

  const exportCurrentLabel = (): ExportedLabelTemplate => {
    return FileUtils.makeExportedLabel(fabricCanvas!, labelProps, csvEnabled);
  };

  const onLoadRequested = (label: ExportedLabelTemplate) => {
    loadLabelData(label).then(() => undo.push(fabricCanvas!, labelProps));
  };
  export const exportLabel = () => exportCurrentLabel();
  export const loadLabel = (label: ExportedLabelTemplate) => onLoadRequested(label);

  const zplImageReady = async (img: Blob) => {
    await LabelDesignerObjectHelper.addImageBlob(fabricCanvas!, img);
    undo.push(fabricCanvas!, labelProps);
  };

  const pdfImageReady = async (el: HTMLCanvasElement) => {
    const img = new fabric.FabricImage(el, {
      ...OBJECT_DEFAULTS,
      left: 0,
      top: 0,
    });

    fabricCanvas!.add(img);
    fabricCanvas!.setActiveObject(img);
    undo.push(fabricCanvas!, labelProps);
  };

  const onObjectPicked = (objectType: OjectType) => {
    if (isNative && (objectType === "qrcode" || objectType === "barcode")) {
      codeEditor = { kind: objectType };
      return;
    }
    if (objectType === "image") {
      LabelDesignerObjectHelper.addImageWithFilePicker(fabricCanvas!)
        .then((obj) => {
          fabricCanvas!.setActiveObject(obj);
          undo.push(fabricCanvas!, labelProps);
        })
        .catch(console.error);
      return;
    }
    const obj = LabelDesignerObjectHelper.addObject(fabricCanvas!, objectType);
    if (obj !== undefined) {
      fabricCanvas!.setActiveObject(obj);
      undo.push(fabricCanvas!, labelProps);
    }
  };

  const editCode = () => {
    if (selectedObject instanceof QRCode) codeEditor = { kind: "qrcode", existing: selectedObject };
    if (selectedObject instanceof Barcode) codeEditor = { kind: "barcode", existing: selectedObject };
  };

  const saveCode = (content: CodeContent) => {
    let object = codeEditor?.existing;
    if (object instanceof QRCode) {
      object.set({ text: content.text, ecl: content.ecl, mode: "Byte", qrVersion: 0, quietZone: 4 });
    } else if (object instanceof Barcode) {
      object.set({ encoding: content.encoding, text: content.text, printText: content.printText });
    } else if (content.kind === "qrcode") {
      const available = Math.min(labelProps.size.width, labelProps.size.height) - 8;
      const scale = Math.max(1, Math.min(3, Math.floor(available / (content.modules + 8))));
      const size = Math.ceil(((content.modules + 8) * scale) / 2) * 2;
      object = new QRCode({
        ...OBJECT_DEFAULTS,
        width: size,
        height: size,
        text: content.text,
        ecl: content.ecl,
        quietZone: 4,
      });
      fabricCanvas!.add(object);
      fabricCanvas!.centerObject(object);
    } else {
      object = new Barcode({
        ...OBJECT_DEFAULTS,
        text: content.text,
        encoding: content.encoding,
        printText: content.printText,
        height: Math.max(24, Math.min(64, labelProps.size.height - 16)),
      });
      fabricCanvas!.add(object);
      fabricCanvas!.centerObject(object);
    }
    object.setCoords();
    object.dirty = true;
    fabricCanvas!.setActiveObject(object);
    fabricCanvas!.requestRenderAll();
    undo.push(fabricCanvas!, labelProps);
    editRevision++;
  };

  const onIconPicked = (i: MaterialIcon) => {
    // todo: icon is not vertically centered
    LabelDesignerObjectHelper.addStaticText(fabricCanvas!, String.fromCodePoint(iconCodepoints[i]), {
      fontFamily: "Material Icons",
      fontSize: 100,
    });
    undo.push(fabricCanvas!, labelProps);
  };

  const onSvgIconPicked = (i: string) => {
    LabelDesignerObjectHelper.addSvg(fabricCanvas!, i);
    undo.push(fabricCanvas!, labelProps);
  };

  const openPreview = () => {
    printNow = false;
    previewOpened = true;
  };

  const openPreviewAndPrint = () => {
    printNow = true;
    previewOpened = true;
  };

  const controlValueUpdated = () => {
    if (selectedObject) {
      selectedObject.setCoords();
      selectedObject.dirty = true;
      undo.push(fabricCanvas!, labelProps);
    }
    fabricCanvas!.requestRenderAll();

    // trigger reactivity for controls
    editRevision++;
  };

  const getCanvasForPreview = (): FabricJson => {
    return fabricCanvas!.toJSON();
  };

  const onCsvPlaceholderPicked = (name: string) => {
    const obj = LabelDesignerObjectHelper.addText(fabricCanvas!, `{${name}}`, {
      textAlign: "left",
      originX: "left",
      originY: "top",
    });
    fabricCanvas!.setActiveObject(obj);
    undo.push(fabricCanvas!, labelProps);
  };

  const onPaste = async (event: ClipboardEvent) => {
    if (LabelDesignerUtils.isAnyInputFocused(fabricCanvas!)) {
      return;
    }

    const openedDropdowns = document.querySelectorAll(".dropdown-menu.show");
    if (openedDropdowns.length > 0) {
      return;
    }

    if (event.clipboardData != null) {
      event.preventDefault();
      const obj = await LabelDesignerObjectHelper.addObjectFromClipboard(fabricCanvas!, event.clipboardData);

      if (obj !== undefined) {
        fabricCanvas!.setActiveObject(obj);
        undo.push(fabricCanvas!, labelProps);
      }
    }
  };

  const clearCanvas = () => {
    if (!confirm($tr("editor.clear.confirm"))) {
      return;
    }
    undo.push(fabricCanvas!, labelProps);
    fabricCanvas!.clear();
  };

  const toggleGrid = () => {
    const newVal = !$appConfig.gridEnabled;
    appConfig.update((cfg) => ({ ...cfg, gridEnabled: newVal }));
    fabricCanvas?.setGridEnabled(newVal);
  };

  const loadLabelFromUrl = async () => {
    try {
      const urlTemplate = await FileUtils.readLabelFromUrl();

      if (urlTemplate !== null && confirm($tr("params.saved_labels.load.url.warn"))) {
        onLoadRequested(urlTemplate);
        Toasts.message($tr("params.saved_labels.load.url.loaded"));
        return true;
      }
    } catch (e) {
      Toasts.error(e);
    }
    return false;
  };

  const loadDefaultLabel = async () => {
    const urlLoaded = await loadLabelFromUrl();

    if (urlLoaded) {
      return false;
    }

    try {
      const defaultTemplate = LocalStoragePersistence.loadDefaultTemplate();

      if (defaultTemplate !== null) {
        await loadLabelData(defaultTemplate);
        return false;
      }
    } catch (e) {
      Toasts.error(e);
    }

    LabelDesignerObjectHelper.addText(fabricCanvas!, $tr("editor.default_text"));
    return true;
  };

  const renderOnFontsChanged = () => {
    fabricCanvas?.forEachObject((o) => {
      if (o instanceof fabric.Textbox) {
        o.dirty = true;
      }
    });
    fabricCanvas?.requestRenderAll();
  };

  onMount(async () => {
    const mountedAt = performance.now();
    try {
      const savedLabelProps = LocalStoragePersistence.loadLastLabelProps();
      if (savedLabelProps !== null) {
        labelProps = savedLabelProps;
      }
    } catch (e) {
      Toasts.zodErrors(e, "Label parameters load error:");
    }

    fabricCanvas = new CustomCanvas(htmlCanvas, {
      width: labelProps.size.width,
      height: labelProps.size.height,
    });
    fabricCanvas.setLabelProps(labelProps);
    fabricCanvas.onZoomChange = (z, source) => {
      zoomText = Math.round(z * 100) + "%";
      if (source === "user") zoomMode = "manual";
      requestAnimationFrame(updateClipState);
    };
    fabricCanvas.setGridEnabled(!!$appConfig.gridEnabled);

    let restored = false;
    if (isNative) {
      try {
        const draft = LocalStoragePersistence.loadAndValidateObject("studio_draft", ExportedLabelTemplateSchema);
        if (draft) {
          await loadLabelData(draft);
          restored = true;
        }
      } catch (error) {
        console.error("Draft restore failed", error);
      }
    }
    if (!restored && (await loadDefaultLabel())) starterCanvas = JSON.stringify(fabricCanvas.toObject());
    // Older NiimStudio drafts did not record a stock shape. Show the ordinary
    // die-cut label shape by default, without changing explicit rectangular stock.
    if (isNative) {
      const legacyDraft = restored && localStorage.getItem("studio_stock_preview_version") === null;
      if (labelProps.shape === undefined || (legacyDraft && labelProps.shape === "rect")) {
        labelProps = { ...labelProps, shape: "rounded_rect" };
      }
      try {
        localStorage.setItem("studio_stock_preview_version", "1");
      } catch (error) {
        console.warn("Could not store stock-preview preference", error);
      }
    }
    if (isNative) fitCanvasToViewport();
    draftReady = true;
    if (isNative) window.__niimstudioPrepareClose = saveDraft;
    window.addEventListener("beforeunload", saveDraft);

    window.addEventListener("hashchange", loadLabelFromUrl);

    undo.push(fabricCanvas, labelProps);

    // force close dropdowns on touch devices
    fabricCanvas.on("mouse:down", (): void => {
      const dropdowns = document.querySelectorAll("[data-bs-toggle='dropdown']");
      dropdowns.forEach((el) => new Dropdown(el).hide());
    });

    fabricCanvas.on("object:moving", (e): void => {
      if (e.target && e.target.left !== undefined && e.target.top !== undefined) {
        e.target.set({
          left: Math.round(e.target.left / GRID_SIZE) * GRID_SIZE,
          top: Math.round(e.target.top / GRID_SIZE) * GRID_SIZE,
        });
      }
    });

    fabricCanvas.on("object:modified", (): void => {
      undo.push(fabricCanvas!, labelProps);
    });

    fabricCanvas.on("text:changed", () => {
      editRevision++;
      scheduleDraft();
    });
    fabricCanvas.on("mouse:dblclick", (event) => {
      if (isNative && (event.target instanceof QRCode || event.target instanceof Barcode)) {
        codeEditor = { kind: event.target instanceof QRCode ? "qrcode" : "barcode", existing: event.target };
      }
    });

    fabricCanvas.on("object:removed", (): void => {
      undo.push(fabricCanvas!, labelProps);
    });

    fabricCanvas.on("selection:created", (e): void => {
      selectedCount = e.selected?.length ?? 0;
      selectedObject = e.selected?.length === 1 ? e.selected[0] : undefined;
      editRevision++;
    });

    fabricCanvas.on("selection:updated", (e): void => {
      selectedCount = e.selected?.length ?? 0;
      selectedObject = e.selected?.length === 1 ? e.selected[0] : undefined;
      editRevision++;
    });

    fabricCanvas.on("selection:cleared", (): void => {
      selectedObject = undefined;
      selectedCount = 0;
      editRevision++;
    });

    fabricCanvas.on("dragover", (e): void => {
      e.e.preventDefault();
    });

    fabricCanvas.on("drop:after", async (e): Promise<void> => {
      const dragEvt = e.e as DragEvent;
      dragEvt.preventDefault();

      let dropped = false;

      if (dragEvt.dataTransfer?.files) {
        for (const file of dragEvt.dataTransfer.files) {
          try {
            await LabelDesignerObjectHelper.addImageFile(fabricCanvas!, file);
            dropped = true;
          } catch (e) {
            Toasts.error(e);
          }
        }

        if (dropped) {
          undo.push(fabricCanvas!, labelProps);
        }
      }
    });

    fabricCanvas.on("object:scaling", (e): void => {
      if (!e.target) {
        return;
      }

      CanvasUtils.fixFabricObjectScale(e.target);
    });

    // userFonts.subscribe((e) => {console.log(e); renderOnFontsChanged();});

    if ($automation !== undefined) {
      if ($automation.startPrint !== undefined) {
        if ($automation.startPrint === "immediately") {
          openPreview();
        } else if ($automation.startPrint === "after_connect") {
          const unsubscribe = connectionState.subscribe((st) => {
            if (st === "connected") {
              tick().then(() => unsubscribe());
              openPreviewAndPrint();
            }
          });
        }
      }
    }

    if (isNative) {
      const canvasReadyAt = performance.now();
      await tick();
      await document.fonts.ready;
      const fontsReadyAt = performance.now();
      await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
      let verified = true;
      if (window.__NIIMSTUDIO_LIFECYCLE_MODE__ === "write") {
        const object = fabricCanvas.getObjects().find((item) => item instanceof fabric.IText) as fabric.IText;
        object.set("text", "Immediate-close persistence fixture");
        undo.push(fabricCanvas, labelProps); // Deliberately leave the 500ms autosave pending.
      } else if (window.__NIIMSTUDIO_LIFECYCLE_MODE__ === "verify") {
        verified = fabricCanvas
          .getObjects()
          .some((item) => item instanceof fabric.IText && item.text === "Immediate-close persistence fixture");
      }
      const navigation = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
      await nativeRequest("workspaceReady", {
        verified,
        timings: {
          documentReady: navigation?.domContentLoadedEventEnd ?? 0,
          mountedAt,
          canvasReadyAt,
          fontsReadyAt,
          paintedAt: performance.now(),
        },
      });
    }

    if (window.__NIIMSTUDIO_SMOKE__) {
      if (window.__NIIMSTUDIO_BENCHMARK__) {
        const { benchmarkOverlays } = await import("$/desktop/benchmark_overlays");
        window.__niimstudioSmokeTest = () => benchmarkOverlays(exportCurrentLabel());
        return;
      }
      if (window.__NIIMSTUDIO_RESTART_VERIFY__) {
        window.__niimstudioSmokeTest = async () => {
          const objects = fabricCanvas!.getObjects();
          const qr = objects.find((object) => object instanceof QRCode) as QRCode | undefined;
          const barcodes = objects.filter((object) => object instanceof Barcode) as Barcode[];
          const templates = LocalStoragePersistence.loadLabels();
          const restored =
            qr?.text === "https://example.com/updated" &&
            qr.quietZone === 4 &&
            barcodes.some((object) => object.text === "$)") &&
            barcodes.some((object) => object.text === "5901234123457") &&
            templates.some((template) => template.title === "Smoke template");
          return {
            ok: restored,
            processRestartRestored: restored,
            objects: objects.length,
            templates: templates.length,
          };
        };
        return;
      }
      if (window.__NIIMSTUDIO_DEMO__) {
        const { loadSmokeDemo } = await import("$/desktop/smoke_demo");
        loadSmokeDemo(fabricCanvas);
      }
      const { runEditorSmoke } = await import("$/desktop/smoke");
      window.__niimstudioSmokeTest = () =>
        runEditorSmoke({
          canvas: fabricCanvas!,
          labelProps,
          undo,
          addObject: onObjectPicked,
          exportLabel: exportCurrentLabel,
          loadLabel: loadLabelData,
          saveDraft,
          openPreview,
        });
    }
  });

  onDestroy(() => {
    clearTimeout(draftTimer);
    saveDraft();
    window.removeEventListener("beforeunload", saveDraft);
    delete window.__niimstudioSmokeTest;
    delete window.__niimstudioPrepareClose;
    fabricCanvas!.dispose();
    window.removeEventListener("hashchange", loadLabelFromUrl);
  });

  $effect(() => {
    fabricCanvas?.setLabelProps(labelProps);
  });

  $effect(() => {
    if (!previewOpened) {
      printNow = false;
    }
  });

  $effect(() => {
    if ($loadedFonts) {
      renderOnFontsChanged();
    }
  });

  $effect(() => {
    const width = windowWidth;
    const size = `${labelProps.size.width}x${labelProps.size.height}`;
    if (!isNative || !draftReady || zoomMode !== "fit" || !width || !size) return;
    requestAnimationFrame(fitCanvasToViewport);
  });
</script>

<svelte:window bind:innerWidth={windowWidth} onkeydown={onKeyDown} onpaste={onPaste} />

<div class="image-editor">
  <div class="row mb-3 studio-stage">
    <div class="col d-flex justify-content-center" bind:this={stageColumn}>
      <div
        class="canvas-viewport {clippedX ? 'is-clipped-x' : ''} {clippedY ? 'is-clipped-y' : ''}"
        bind:this={canvasViewport}
        onscroll={updateClipState}>
        <div
          class="canvas-wrapper print-start-{labelProps.printDirection} label-shape-{labelProps.shape ?? 'rect'}"
          style:--label-preview-radius={`${Number.parseFloat(zoomText) / 10}px`}>
          <canvas bind:this={htmlCanvas}></canvas>
        </div>
      </div>
      {#if isNative}<div class="studio-canvas-caption">
          {labelProps.size.width} × {labelProps.size.height} px · Ctrl + scroll to zoom · middle-drag to pan · {draftState}
          {#if clippedX || clippedY}<span class="studio-canvas-clip-note">
              · Zoomed in: scroll to see the full label</span
            >{/if}
        </div>{/if}
    </div>
  </div>

  <div class="row mb-1 studio-actions">
    <div class="col d-flex justify-content-center">
      <div class="toolbar d-flex flex-wrap gap-1 justify-content-center align-items-center">
        {#if isNative}
          <StockSetup
            current={labelProps}
            blocked={!draftReady || previewOpened || $printJobActive || !!codeEditor}
            hasArtwork={() =>
              !!fabricCanvas?.getObjects().length && JSON.stringify(fabricCanvas.toObject()) !== starterCanvas}
            onApply={(stock) =>
              onUpdateLabelProps({
                ...labelProps,
                size: stock.size,
                printDirection: stock.printDirection,
                shape: stock.shape,
              })} />
        {:else}
          <LabelPropsEditor {labelProps} onChange={onUpdateLabelProps} />
        {/if}

        {#if !isNative}
          <button class="btn btn-sm btn-secondary" onclick={clearCanvas} title={$tr("editor.clear")}>
            <MdIcon icon="cancel_presentation" />
          </button>

          <SavedLabelsMenu
            canvas={fabricCanvas!}
            onRequestLabelTemplate={exportCurrentLabel}
            {onLoadRequested}
            {csvEnabled} />
        {/if}

        <button
          class="btn btn-sm btn-secondary"
          disabled={undoState.undoDisabled}
          onclick={() => undo.undo()}
          title={$tr("editor.undo")}>
          <MdIcon icon="undo" />
        </button>

        <button
          class="btn btn-sm btn-secondary"
          disabled={undoState.redoDisabled}
          onclick={() => undo.redo()}
          title={$tr("editor.redo")}>
          <MdIcon icon="redo" />
        </button>

        <button
          class="btn btn-sm {$appConfig.gridEnabled ? 'btn-primary' : 'btn-secondary'}"
          onclick={toggleGrid}
          title={$tr("editor.grid")}>
          <MdIcon icon="grid_on" />
        </button>

        <button
          class="btn btn-sm btn-secondary"
          data-action="fit-zoom"
          onclick={fitCanvasToViewport}
          title="Fit the whole label in the viewing area">
          <MdIcon icon="fit_screen" />
          {zoomText}
        </button>

        {#if !isNative}
          <CsvControl bind:enabled={csvEnabled} onPlaceholderPicked={onCsvPlaceholderPicked} />

          <IconPicker onSubmit={onIconPicked} onSubmitSvg={onSvgIconPicked} />

          <ObjectPicker onSubmit={onObjectPicked} {labelProps} {zplImageReady} {pdfImageReady} />
        {/if}

        <button class="btn btn-sm btn-secondary ms-1 studio-preview-action" onclick={openPreview}>
          <MdIcon icon="visibility" />
          {$tr("editor.preview")}
        </button>
        <button
          title="Print with default or saved parameters"
          class="btn btn-sm btn-primary ms-1"
          onclick={openPreviewAndPrint}
          disabled={$connectionState !== "connected"}><MdIcon icon="print" /> {$tr("editor.print")}</button>
      </div>
    </div>
  </div>

  {#snippet objectProperties()}
    {#if selectedObject && selectedCount === 1}<GenericObjectParamsControls
        {selectedObject}
        {editRevision}
        valueUpdated={controlValueUpdated} />{/if}
    {#if selectedObject}<VectorParamsControls {selectedObject} {editRevision} valueUpdated={controlValueUpdated} />{/if}
    {#if selectedObject instanceof fabric.IText}<TextParamsControls
        selectedText={selectedObject}
        {editRevision}
        valueUpdated={controlValueUpdated} />{/if}
    {#if selectedObject instanceof QRCode}<QrCodeParamsPanel
        selectedQRCode={selectedObject}
        {editRevision}
        valueUpdated={controlValueUpdated} />{/if}
    {#if selectedObject instanceof ArUcoMarker}<ArUcoParamsPanel
        selectedArUco={selectedObject}
        {editRevision}
        valueUpdated={controlValueUpdated} />{/if}
    {#if selectedObject instanceof Barcode}<BarcodeParamsPanel
        selectedBarcode={selectedObject}
        {editRevision}
        valueUpdated={controlValueUpdated} />{/if}
    {#if selectedObject instanceof fabric.IText || selectedObject instanceof QRCode || (selectedObject instanceof Barcode && selectedObject.encoding === "CODE128B")}<VariableInsertControl
        {selectedObject}
        valueUpdated={controlValueUpdated} />{/if}
  {/snippet}

  {#if isNative}
    <SelectionToolbar
      {selectedObject}
      {selectedCount}
      {editRevision}
      valueUpdated={controlValueUpdated}
      clone={cloneSelected}
      remove={deleteSelected}
      {editCode}>
      {@render objectProperties()}
    </SelectionToolbar>
    <div class="studio-insert-toolbar" role="group" aria-label="Add label content">
      <button class="btn studio-insert-button" onclick={() => onObjectPicked("text")}
        ><MdIcon icon="title" /><span>Text</span></button>
      <button class="btn studio-insert-button" onclick={() => onObjectPicked("image")}
        ><MdIcon icon="image" /><span>Image</span></button>
      <button class="btn studio-insert-button" data-action="insert-qrcode" onclick={() => onObjectPicked("qrcode")}
        ><MdIcon icon="qr_code_2" /><span>QR code</span></button>
      <button class="btn studio-insert-button" data-action="insert-barcode" onclick={() => onObjectPicked("barcode")}
        ><MdIcon icon="view_week" /><span>Barcode</span></button>
      <div class="dropdown">
        <button class="btn studio-insert-button" data-bs-toggle="dropdown" aria-label="Insert a shape"
          ><MdIcon icon="category" /><span>Shapes</span></button>
        <div class="dropdown-menu">
          <button class="dropdown-item" onclick={() => onObjectPicked("rectangle")}>Rectangle</button>
          <button class="dropdown-item" onclick={() => onObjectPicked("circle")}>Circle</button>
          <button class="dropdown-item" onclick={() => onObjectPicked("line")}>Line</button>
        </div>
      </div>
      <IconPicker onSubmit={onIconPicked} onSubmitSvg={onSvgIconPicked} label="Icons" />
      <CsvControl bind:enabled={csvEnabled} onPlaceholderPicked={onCsvPlaceholderPicked} label="Data" />
      <ObjectPicker onSubmit={onObjectPicked} {labelProps} {zplImageReady} {pdfImageReady} label="More" advancedOnly />
      <div class="dropdown studio-document-menu">
        <button class="btn studio-insert-button" title="Document options" data-bs-toggle="dropdown"
          ><MdIcon icon="tune" /><span>Document</span></button>
        <div class="dropdown-menu p-2">
          <button class="dropdown-item" onclick={clearCanvas}>Clear label…</button>
          <div class="studio-help px-3 py-2">Library import/export is in Templates.</div>
        </div>
      </div>
    </div>
  {:else}
    <div class="row mb-1">
      <div class="col d-flex justify-content-center">
        <div class="toolbar d-flex flex-wrap gap-1 justify-content-center align-items-center">
          {#if selectedCount > 0}
            <button class="btn btn-sm btn-danger me-1" onclick={deleteSelected} title={$tr("editor.delete")}>
              <MdIcon icon="delete" />
            </button>
          {/if}

          {#if selectedCount > 0}
            <button class="btn btn-sm btn-secondary me-1" onclick={cloneSelected} title={$tr("editor.clone")}>
              <MdIcon icon="content_copy" />
            </button>
          {/if}

          {@render objectProperties()}
        </div>
      </div>
    </div>
  {/if}

  {#if codeEditor}
    <CodeEditor
      kind={codeEditor.kind}
      existing={codeEditor.existing}
      availableWidth={labelProps.size.width - 8}
      availableHeight={labelProps.size.height - 8}
      onSave={saveCode}
      onClose={() => (codeEditor = undefined)} />
  {/if}

  {#if previewOpened}
    <PrintPreview
      bind:show={previewOpened}
      canvasCallback={getCanvasForPreview}
      {labelProps}
      {printNow}
      {csvEnabled}
      csvData={$csvData.data} />
  {/if}
</div>

<style>
  .canvas-viewport {
    width: fit-content;
    max-width: 100%;
    max-height: 70vh;
    overflow: auto;
    line-height: 0;
  }
  .canvas-viewport.is-clipped-x,
  .canvas-viewport.is-clipped-y {
    outline: 1px dashed color-mix(in srgb, var(--studio-accent) 60%, transparent);
    outline-offset: 4px;
  }
  .canvas-wrapper {
    display: block;
    width: max-content;
    border: 1px solid rgba(0, 0, 0, 0.4);
    background-color: rgba(60, 55, 63, 0.5);
  }
  .studio-canvas-clip-note {
    color: var(--studio-accent);
  }
  .canvas-wrapper.print-start-left {
    border-left: 2px solid #ff4646;
  }
  .canvas-wrapper.print-start-top {
    border-top: 2px solid #ff4646;
  }
  .canvas-wrapper canvas {
    image-rendering: pixelated;
    display: block;
  }
</style>
