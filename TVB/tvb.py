from models import *
import numpy as np
import os
from tvb_utils import *
from huggingface_hub import hf_hub_download
from logger import logger

SUPPORTED_MODELS = [
                    '1CNN',
                    '3CNN',
                    '3DNN',
                    'CNNLSTM',
                    'Seq_CNNLSTM',
                    'Seq_CNNLSTM_1sec'
                    ]

class TVB_handler():
    def __init__(self,
                pretrained_model_name,
                load_weights=True,
                custom_model=False,
                mode='predict',
                get_f1=True,
                get_acc=True,
                window_size=300,
                stride=300,
                normalisation='minmax',
                tensordataset=True,
                batch_size=4,
                collate_fn=None,
                num_workers=2,
                shuffle=False,
                device='cuda',
                progressbar=True,
                model_cache_dir='.cache_dir',
                repo_id="viks66/TVB",
                ):
        raiseException(mode, '==', 'predict')
        if pretrained_model_name not in SUPPORTED_MODELS:
            raise Exception(f'{pretrained_model_name} should be from {SUPPORTED_MODELS}')
        logger.info(f"Using {pretrained_model_name} model")
        self.pretrained_model_name = pretrained_model_name
        self.window_size = window_size
        self.stride = stride
        self.normalisation = normalisation
        self.tensordataset = tensordataset
        self.batch_size = batch_size
        self.collate_fn = collate_fn
        self.num_workers = num_workers
        self.shuffle = shuffle
        self.device = device
        self.progressbar = progressbar
        self.model_cache_dir = model_cache_dir
        self.repo_id = repo_id
        self.model = self.get_pretrained_model(pretrained_model_name)
        if load_weights:
            self.download_and_load_weights()

    def get_pretrained_model(self, modelname):
        models = {
                'CNNLSTM':CNNLSTM,
                '1CNN':CNN1 ,
                '3CNN':CNN3,
                '3DNN':DNN3,
                'Seq_CNNLSTM':Seq_CNNLSTM,
                'Seq_CNNLSTM_1sec': Seq_CNNLSTM_1sec,
                }
        params = models[modelname].info()
        kernel_stride_info = models[modelname].kernel_stride_info()
        if kernel_stride_info["kernel"] != self.window_size:
            logger.info(f'Changing window size according to model training configuration to {kernel_stride_info["kernel"]}')
            self.window_size = kernel_stride_info["kernel"]
        if kernel_stride_info["stride"] != self.stride:
            logger.info(f'Changing shift size according to model training configuration to {kernel_stride_info["stride"]}')
            self.stride = kernel_stride_info["stride"]
        return models[modelname](**params)

    def download_and_load_weights(self):
        model_names = {
                    'CNNLSTM':'1cnn_fold2.pth',
                    '1CNN':'final_actual_1cnn_fold2.pth' ,
                    '3CNN':'final_actual_3cnn_fold2.pth',
                    '3DNN':'final_actual_3dnn_fold2.pth',
                    'Seq_CNNLSTM_1sec':'seq_cnn_lstm_1sec_fold2_300.pth',
                    'Seq_CNNLSTM':'seq_cnn_lstm_fold2_300.pth',
                    }
        if os.path.exists(os.path.join(self.model_cache_dir, model_names[self.pretrained_model_name])):
            logger.info(f'pretrained model weights for {self.pretrained_model_name} found at {self.model_cache_dir}')
        else:
            logger.info(f'pretrained model weights for {self.pretrained_model_name} not found at {self.model_cache_dir}, Downloading..')
            hf_hub_download(
                            repo_id=self.repo_id,
                            filename=model_names[self.pretrained_model_name],
                            cache_dir=self.model_cache_dir,
                            force_filename=model_names[self.pretrained_model_name]
                            )
            logger.info(f'Weights stored at {self.model_cache_dir}')
        self.model.load_state_dict(torch.load(os.path.join(self.model_cache_dir, model_names[self.pretrained_model_name])))
        logger.info(f'Loaded weights into model')

    def predict(self,
                data,
                custom_metric=None,
                display_model=False,
                display_model_info=False
                ):
        if display_model:
            print(self.model)
        if display_model_info:
            a = self.model.info()
            print(a)
        data = read_data(data)

        data = make_numpyloader(data, self.window_size, self.stride, self.normalisation)
        results = pred_from_numpy(data, self.model, self.device, self.window_size, self.tensordataset, self.batch_size,
                        self.collate_fn, self.num_workers, self.shuffle, self.progressbar)
        return results
