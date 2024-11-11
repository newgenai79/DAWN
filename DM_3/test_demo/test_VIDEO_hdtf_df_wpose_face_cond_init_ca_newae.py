# test a video flow diffusion model based on RegionMM for crema dataset\
# 20ckp，iddiffused head
import sys
sys.path.append('your/path/DAWN-pytorch')
import argparse

import imageio
import torch
from torch.utils import data
import numpy as np
import torch.backends.cudnn as cudnn
import os
import timeit
from PIL import Image
from misc import grid2fig, conf2fig
from DM.datasets_hdtf_wpose_lmk_block import HDTF
import random
from DM_3.modules.video_flow_diffusion_model_multiGPU_v0_crema_vgg_floss_plus_faceemb_flow_fast_init_cond_test import FlowDiffusion
# to save videos
import cv2
import tempfile
from subprocess import call
from pydub import AudioSegment
import re
from torchvision import transforms
import time
start = timeit.default_timer()
BATCH_SIZE = 1
MAX_N_FRAMES = 200
root_dir = 'your_path'
# data_dir='/work1/cv2/pcxia/diffusion_v1/diffused-heads-colab-main/datasets/images'
data_dir = "/train20/intern/permanent/hbcheng2/data/HDTF/images_25hz_128_chunk"
pose_dir = "/train20/intern/permanent/hbcheng2/data/HDTF/pose_bar_chunk"
eye_blink_dir = "/train20/intern/permanent/hbcheng2/data/HDTF/eye_blink_bbox_from_xpc_bar_2_chunk"
GPU = "0"
postfix = "-j-of-tr-ddim"
# default value
ddim_sampling_eta = 1.0
POSE_DIM = 6# 7
timesteps = 1000
if "ddim" in postfix:
    sampling_step = 20
    ddim_sampling_eta = 1.0
    postfix = postfix + "%04d_%.2f" % (sampling_step, ddim_sampling_eta)
else:
    sampling_step = 1000
INPUT_SIZE = 128
N_FRAMES = 20
RANDOM_SEED = 1234
NUM_VIDEOS = 50
WIN_WIDTH = 40
NUM_ITER = NUM_VIDEOS // BATCH_SIZE
MEAN = (0.0, 0.0, 0.0)
cond_scale = 1.0
# the path to trained DM
# RESTORE_FROM = "your_path/data/log_dm_crema/ODOA_v0_Fn=20/snapshots-j-of/flowdiff_0008_S300000.pth"
# RESTORE_FROM = "your_path/data/log_dm_crema/v0_lr_maxFn=20/snapshots-j-of/flowdiff.pth"
# RESTORE_FROM = "your/path/DAWN-pytorch/data/solve_oom/log_dm_crema/1_newae_v0_Fn=20/snapshots-j-of/flowdiff.pth"
# RESTORE_FROM = 'your/path/DAWN-pytorch/data/origin/log_dm_crema/1_newae_v0_Fn=20/snapshots-j-of/flowdiff.pth'
# RESTORE_FROM = 'your_path/data/log_dm_crema/obj_v0_Fn=20/snapshots-j-of/flowdiff_0008_S350000.pth'
# RESTORE_FROM = 'your/path/DAWN-pytorch/data/dfhd_obj_oldAE/log_dm_crema/1_newae_v0_Fn=20/snapshots-j-of/flowdiff_0012_S293000.pth'
# RESTORE_FROM = 'your_path/data/log_dm_hdtf/oldae_v0_lr_N=20/snapshots-j-of/flowdiff_copy.pth'
# RESTORE_FROM = 'your/path/DAWN-pytorch/data/HDTF_wpose_faceemb_newae/ca_init_cond_liploss/2_stage3_rand_df_from_ckpt_liploss_lr=6_N=40/snapshots-j-of-s2/flowdiff_0040_S200000.pth'
RESTORE_FROM = 'your/path/DAWN-pytorch/data/HDTF_wpose_faceemb_newae_6Dpose/ca_em_mask/stage3_rand_df_from_ckpt_liploss_lr_N=40/snapshots-j-of-s2/flowdiff_0040_S200000.pth'
# RESTORE_FROM = 'your_path/data/log_dm_hdtf/start0_v0_lr_N=10/snapshots-j-of/flowdiff.pth'
name = 'DF_' + str(MAX_N_FRAMES) +'_'+ RESTORE_FROM.split('/')[9] + '_' + RESTORE_FROM.split('/')[11].split('.')[0]+'_ddim'+str(sampling_step)
# name = 'DF_bjd_' + RESTORE_FROM.split('/')[8] + '_' + RESTORE_FROM.split('/')[12].split('.')[0]
AE_RESTORE_FROM = 'your/path/DAWN-pytorch/AE/data/log-hdtf-cosin/hdtf128_1000ep_2024-08-08_15:04/snapshots/RegionMM.pth'   #hdtf

# AE_RESTORE_FROM = "your_path/data/log-hdtf/hdtf128_2024-01-06_21:35/snapshots/RegionMM.pth" # old AE for crema
# AE_RESTORE_FROM = 'your_path/data/log-hdtf/hdtf128_2024-02-11_15:45/snapshots/RegionMM_0100_S074360.pth'  # new AE for crema
# CKPT_DIR = os.path.join(root_dir, 'demo','test_ndna30w_-1_notall_fstart_reg_v0_19'+postfix)

DATASAVE_DIR = '/train20/intern/permanent/hbcheng2/data'
CKPT_DIR = os.path.join(DATASAVE_DIR, 'hdtf_wpose_faceemb_1','cross_test_WRA_CandiceMiller0_000', name + f'WIN{WIN_WIDTH}','video')
os.makedirs(CKPT_DIR, exist_ok=True)
IMG_DIR = os.path.join(DATASAVE_DIR, 'hdtf_wpose_faceemb_1','cross_test_WRA_CandiceMiller0_000', name + f'WIN{WIN_WIDTH}','img')
os.makedirs(IMG_DIR, exist_ok=True)
print(root_dir)
print(DATASAVE_DIR)
print(postfix)
print("RESTORE_FROM:", RESTORE_FROM)
print("cond scale:", cond_scale)
print("sampling step:", sampling_step)


def get_arguments():
    """Parse all the arguments provided from the CLI.

    Returns:
      A list of parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Flow Diffusion")
    parser.add_argument("--num-workers", default=8)
    parser.add_argument("--gpu", default=GPU,
                        help="choose gpu device.")
    parser.add_argument('--print-freq', '-p', default=10, type=int,
                        metavar='N', help='print frequency')
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                        help="Number of images sent to the network in one step.")
    parser.add_argument("--input-size", type=str, default=INPUT_SIZE,
                        help="Comma-separated string with height and width of images.")
    parser.add_argument("--random-seed", type=int, default=RANDOM_SEED,
                        help="Random seed to have reproducible results.")
    parser.add_argument("--restore-from", default=RESTORE_FROM)
    parser.add_argument("--fp16", default=False)
    return parser.parse_args()


args = get_arguments()

def extract_audio_by_frames(input_wav_path, start_frame_index, num_frames, frame_rate, output_wav_path):
    # 
    audio = AudioSegment.from_wav(input_wav_path)

    # 
    frame_duration = 1000 / frame_rate  # 

    # 
    start_time_ms = start_frame_index * frame_duration
    end_time_ms = (start_frame_index + num_frames) * frame_duration

    # 
    selected_audio = audio[start_time_ms:end_time_ms]

    # 
    selected_audio.export(output_wav_path, format="wav")

def get_block_data(path, start, end):
    # TODO： id function
    '''
    input: 
        start: start id
        end:  end id
    output:
        the data from block
    '''

    block_st = start//25
    block_ed = end//25

    st_pos = start % 25
    ed_pos = end % 25

    block_list = [os.path.join(path,'chunk_%04d.npy' % (i)) for i in range(block_st, block_ed+1)]

    if block_st != block_ed:
        arr_list = []
        block_st = np.load(block_list[0])
        arr_list.append(block_st[st_pos:])
        for path in block_list[1:-1]:
            arr_list.append(np.load(path))

        block_ed = np.load(block_list[-1])
        arr_list.append(block_ed[:ed_pos])

        return np.concatenate(arr_list)
    else:
        block_st_path = os.path.join(path, block_list[0])
        block_st = np.load(block_st_path)
        return block_st[st_pos: ed_pos]

def sample_img(rec_img_batch, index):
    rec_img = rec_img_batch[index].permute(1, 2, 0).data.cpu().numpy().copy()
    rec_img += np.array(MEAN)/255.0
    rec_img[rec_img < 0] = 0
    rec_img[rec_img > 1] = 1
    rec_img *= 255
    return np.array(rec_img, np.uint8)

def main():
    """Create the model and start the training."""

    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu

    cudnn.enabled = True
    cudnn.benchmark = True
    setup_seed(args.random_seed)

    model = FlowDiffusion(is_train=True,
                          sampling_timesteps=sampling_step,
                          ddim_sampling_eta=ddim_sampling_eta,
                          pose_dim = POSE_DIM,
                          num_frames=N_FRAMES,
                          config_pth="your/path/DAWN-pytorch/config/hdtf128.yaml",
                          pretrained_pth=AE_RESTORE_FROM,
                          win_width = WIN_WIDTH)
    model.cuda()

    if args.restore_from:
        if os.path.isfile(args.restore_from):
            print("=> loading checkpoint '{}'".format(args.restore_from))
            checkpoint = torch.load(args.restore_from)
            model.diffusion.load_state_dict(checkpoint['diffusion'])
            print("=> loaded checkpoint '{}'".format(args.restore_from))
        else:
            print("=> no checkpoint found at '{}'".format(args.restore_from))
            exit(-1)
    else:
        print("NO checkpoint found!")
        exit(-1)

    model.eval()

    # real_vids, ref_hubert, real_poses, real_blink_bbox, real_names, start_frame_index

    ref_face_ids = ['RD_Radio14_000','RD_Radio30_000','RD_Radio47_000','RD_Radio56_000','WDA_AmyKlobuchar1_001',\
                            'WDA_BarbaraLee0_000','WDA_BobCasey0_000','WDA_CatherineCortezMasto_000','WDA_DebbieDingell1_000','WDA_DonaldMcEachin_000',\
                            'WDA_EricSwalwell_000','WDA_HenryWaxman_000','WDA_JanSchakowsky1_000','WDA_JoeDonnelly_000','WDA_JohnSarbanes1_000',\
                            'WDA_JoeNeguse_001','WDA_KatieHill_000','WDA_LucyMcBath_000','WDA_MazieHirono0_000','WDA_NancyPelosi1_000',\
                            'WDA_PattyMurray0_000','WDA_RaulRuiz_000','WDA_SeanPatrickMaloney_000','WDA_TammyBaldwin0_000','WDA_TerriSewell0_000',\
                            'WDA_TomCarper_000','WDA_WhipJimClyburn_000','WRA_AdamKinzinger0_000','WRA_AnnWagner_000','WRA_BobCorker_000',\
                            'WRA_CandiceMiller0_000','WRA_CathyMcMorrisRodgers2_000','WRA_CoryGardner1_000','WRA_DebFischer1_000','WRA_DianeBlack1_000',\
                            'WRA_ErikPaulsen_000','WRA_GeorgeLeMieux_000','WRA_JebHensarling0_001','WRA_JoeHeck1_000','WRA_JohnKasich1_001',\
                            'WRA_MarcoRubio_000'] # 'WDA_NancyPelosi1_000' # 'WDA_NancyPelosi1_000' # 'WRA_JohnKasich1_001'
    for ref_face_id in ref_face_ids:
        drive_face_id = 'WRA_CandiceMiller0_000'
        ref_hubert_path = f'/train20/intern/permanent/hbcheng2/data/HDTF/hdtf_wav_hubert_interpolate/{drive_face_id}.npy'
        drive_pose_path = f'/train20/intern/permanent/hbcheng2/data/HDTF/pose_bar/{drive_face_id}.npy'
        real_pose_path = f'/train20/intern/permanent/hbcheng2/data/HDTF/pose_bar/{ref_face_id}.npy'
        ref_img_path = f'/train20/intern/permanent/hbcheng2/data/HDTF/images_25hz_128/{ref_face_id}/0000000.jpg'
        real_blink_bbox_path = f'/train20/intern/permanent/hbcheng2/data/HDTF/eye_blink_bbox_from_xpc_bar/{ref_face_id}.npy'
        drive_blink_path = f'/train20/intern/permanent/hbcheng2/data/HDTF/eye_blink_bbox_from_xpc_bar/{drive_face_id}.npy'
        
        video_path = '/train20/intern/permanent/hbcheng2/data/HDTF/images_25hz_128_chunk'

        ref_id = int(ref_img_path.split('/')[-1][:-4])
        image = Image.open(ref_img_path)

        real_vids = torch.from_numpy(get_block_data(os.path.join(video_path, drive_face_id), 0 , 200)).permute(3, 0 ,1, 2).unsqueeze(0)

        # 
        transform = transforms.Compose([
            transforms.ToTensor()
        ])

        image_tensor = transform(image) * 255
        # MAX_N_FRAMES
        ref_hubert = torch.from_numpy(np.load(ref_hubert_path)[:MAX_N_FRAMES]).to(torch.float32)
        real_poses = torch.from_numpy(np.load(real_pose_path)[:MAX_N_FRAMES]).to(torch.float32)
        drive_poses = torch.from_numpy(np.load(drive_pose_path)[:MAX_N_FRAMES]).to(torch.float32)
        drive_blink_bbox = torch.from_numpy(np.load(drive_blink_path)[:MAX_N_FRAMES]).to(torch.float32)
        real_blink_bbox = torch.from_numpy(np.load(real_blink_bbox_path)[:MAX_N_FRAMES]).to(torch.float32)

        init_pose = real_poses[ref_id].unsqueeze(0)
        init_blink = real_blink_bbox[ref_id,:2].unsqueeze(0)

        real_poses = real_poses.permute(1,0)
        drive_poses = drive_poses.permute(1,0)
        drive_blink_bbox = drive_blink_bbox.permute(1,0)
        real_blink_bbox = real_blink_bbox.permute(1,0)


        real_names = ref_hubert_path.split('/')[-1][:-4] # 'WRA_JoeHeck1_000'
        setup_seed(args.random_seed)
        # testloader = data.DataLoader(HDTF(data_dir=data_dir,
        #                                    pose_dir=pose_dir,
        #                                    eye_blink_dir = eye_blink_dir,
        #                                    image_size=INPUT_SIZE,
        #                                    mode='test',
        #                                    max_num_frames=MAX_N_FRAMES,
        #                                    color_jitter=True,
        #                                    mean=MEAN),
        #                              batch_size=args.batch_size,
        #                              shuffle=True, num_workers=args.num_workers,
        #                              pin_memory=True)

        # batch_time = AverageMeter()
        # data_time = AverageMeter()

        iter_end = timeit.default_timer()
        cnt = 0
        
        output_wav_path = tempfile.NamedTemporaryFile('w', suffix='.wav', dir='./').name

        # for i_iter, batch in enumerate(testloader):

        reg_count = 0


        
        fn = MAX_N_FRAMES

        SAV_DIR = os.path.join(CKPT_DIR,  ref_face_id+'.mp4')
        # if os.path.exists(SAV_DIR):
        #     continue

        # 
        tmp_video_file_pred = tempfile.NamedTemporaryFile('w', suffix='.mp4', dir='./')
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 25  # 

        # 
        video_writer = cv2.VideoWriter(tmp_video_file_pred.name, fourcc, fps, (128, 128))

        # 
        wav_path = os.path.join("/yrfs2/cv2/pcxia/audiovisual/hdtf/images_25hz".replace('/images_25hz','/image_audio'), real_names+'.wav')
        # wav_path = os.path.join(testloader.dataset.data_dir.replace('/images','/audio'), real_names[0].replace('_','/',1)+'.wav')
        # start_frame_index = 0
        extract_audio_by_frames(wav_path, 0, fn, fps, output_wav_path)

        # imgs
        img_dir_name = "%s_%.2f" % (ref_face_id, cond_scale)
        cur_img_dir_gt = os.path.join(IMG_DIR, img_dir_name,'gt')
        os.makedirs(cur_img_dir_gt, exist_ok=True)
        cur_img_dir_samp = os.path.join(IMG_DIR, img_dir_name,'samp')
        os.makedirs(cur_img_dir_samp, exist_ok=True)


        # ref_imgs =( real_vids[:, :, 0, :, :].clone().detach())
        bs = 1
        with open('your/path/DAWN-pytorch/speed_test.txt', 'w') as f:
                f.write(f'test_start\n')
        # with torch.no_grad():
        #     train_output_dict = model.forward(real_vid=real_vids_.cuda(), ref_img=ref_imgs.cuda(), ref_text=ref_hubert_.cuda())
        for i in range(1):
            start_time = time.time()  # end
            with torch.cuda.amp.autocast(enabled=True):
                with torch.no_grad():
                    model.update_num_frames(fn)
                    # cond = torch.concat([ref_hubert[0].unsqueeze(dim=0), real_poses[0].permute(1,0).unsqueeze(0), real_blink_bbox[0][:2].permute(1,0).unsqueeze(0)], dim=-1).cuda()  # manually concat pose
                    sample_output_dict = model.sample_one_video(sample_img=image_tensor.unsqueeze(dim=0).cuda()/255.,
                                                                sample_audio_hubert = ref_hubert.unsqueeze(dim=0).cuda(),
                                                                sample_pose = drive_poses.unsqueeze(0).cuda(),
                                                                sample_eye =  drive_blink_bbox[:2].unsqueeze(0).cuda(),
                                                                sample_bbox = real_blink_bbox[2:].unsqueeze(0).cuda(),
                                                                init_pose = init_pose.cuda(),
                                                                init_eye = init_blink.cuda(),
                                                                cond_scale=1.0)
            end_time = time.time()  # end
            with open('your/path/DAWN-pytorch/speed_test.txt', 'a') as f:
                f.write(f'generation time {end_time- start_time}\n')
            print(f'generation time {end_time- start_time}')
            start_time = end_time
        
        msk_size = INPUT_SIZE
        
        for batch_idx in range(bs):

            for frame_idx in range(0,fn):

                new_im_gt = Image.new('RGB', (msk_size, msk_size))
                new_im_sample = Image.new('RGB', (msk_size, msk_size))

                save_sample_out_img = sample_img(sample_output_dict["sample_out_vid"][:, :, frame_idx], batch_idx)
                save_tar_img = sample_img(real_vids[:, :, reg_count+frame_idx]/255., batch_idx)
                # save_real_out_img = sample_img(train_output_dict["real_out_vid"][:, :, frame_idx], batch_idx)

                # save sample videos
                frame_rgb = np.uint8(save_sample_out_img)
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                video_writer.write(frame_bgr)

                # save sample and gt imgs
                new_im_gt.paste(Image.fromarray(save_tar_img, 'RGB'), (0, 0))
                new_im_sample.paste(Image.fromarray(save_sample_out_img, 'RGB'), (0, 0))
                new_im_arr_gt = np.array(new_im_gt)
                new_im_arr_sample = np.array(new_im_sample)
                new_im_name = "%03d_%s_%.2f.png" % (frame_idx+reg_count, ref_face_id, cond_scale)
                imageio.imsave(os.path.join(cur_img_dir_gt,new_im_name), new_im_arr_gt)
                imageio.imsave(os.path.join(cur_img_dir_samp,new_im_name), new_im_arr_sample)
            
        video_writer.release()
        cmd = ('ffmpeg -y ' + ' -i {0} -i {1} -vcodec copy -ac 2 -channel_layout stereo -pix_fmt yuv420p {2} -shortest'.format(
        output_wav_path, tmp_video_file_pred.name, SAV_DIR)).split()   
        call(cmd)  
        iter_end = timeit.default_timer()


        end = timeit.default_timer()
        print(end - start, 'seconds')
        print(CKPT_DIR)
    # print(IMG_DIR)


class AverageMeter(object):
    """Computes and stores the average and current value"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def setup_seed(seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.backends.cudnn.deterministic = True


if __name__ == '__main__':
    main()

