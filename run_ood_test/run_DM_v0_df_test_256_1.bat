@echo off

REM Set variables
set test_name=ood_test_10091
set time_tag=tmp1009
set audio_path=WRA_MarcoRubio_000.wav
set image_path=real_female_1.jpeg
set cache_path=cache\%time_tag%
set audio_emb_path=cache\target_audio.npy
set video_output_path=cache\

REM Activate the 3DDFA Conda environment and run the first script
call conda activate 3DDFA
cd extract_init_states
python demo_pose_extract_2d_lmk_img.py --input ../%image_path% --output ../%cache_path%
cd ..

REM Activate the DAWN Conda environment and run the remaining scripts
call conda activate DAWN

python hubert_extract\data_gen\process_lrs3\process_audio_hubert_interpolate_demo.py --src_audio_path %audio_path% --save_path %audio_emb_path%

python PBNet\src\evaluate\tvae_eval_single_both_eye_pose.py --audio_path %audio_emb_path% --init_pose_blink %cache_path% --ckpt pretrain_models\pbnet_both\checkpoint_100000.pth.tar --output %cache_path%

python DM_3\test_demo\test_VIDEO_hdtf_df_wpose_face_cond_init_ca_newae_ood_256_2.py --gpu 0 --source_img_path %image_path% --init_state_path %cache_path% --drive_blink_path %cache_path%\dri_blink.npy --drive_pose_path %cache_path%\dri_pose.npy --audio_emb_path %audio_emb_path% --save_path %video_output_path%\%test_name% --src_audio_path %audio_path%
