// client/src/components/HomeAssistant/Devices/CameraModal.tsx
import React, { useMemo } from 'react';
import { X, Loader2, AlertTriangle } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from '~/components/ui/';

interface CameraModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entityId: string;
  cameraName?: string;
}

const STREAM_INTERVAL_MS = 500;

const CameraModal: React.FC<CameraModalProps> = ({ open, onOpenChange, entityId, cameraName }) => {

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{cameraName || 'Camera Stream'}</DialogTitle>
          <DialogClose onClick={() => onOpenChange(false)} />
        </DialogHeader>
        <div className="w-full h-[480px] bg-black rounded-b-md flex justify-center items-center">{}</div>
      </DialogContent>
    </Dialog>
  );
};

export default CameraModal;
