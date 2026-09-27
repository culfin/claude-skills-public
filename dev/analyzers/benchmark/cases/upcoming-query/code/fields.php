<?php
/**
 * Course fields. Every course carries nine meta rows (start, end, city, country, organiser,
 * organiser URL, URL, source, import hash).
 */

defined( 'ABSPATH' ) || exit;

const CT_POST_TYPE = 'ct_course';
const CT_START     = 'ct_start';
const CT_END       = 'ct_end';
const CT_CITY      = 'ct_city';

function ct_clean_date( string $value ): string {
	$value = trim( $value );
	$date  = DateTimeImmutable::createFromFormat( '!Y-m-d', $value );
	return ( $date && $date->format( 'Y-m-d' ) === $value ) ? $value : '';
}

function ct_shape( int $post_id ): ?array {
	$start = ct_clean_date( (string) get_post_meta( $post_id, CT_START, true ) );
	if ( '' === $start ) {
		return null;
	}
	return [
		'id'    => $post_id,
		'title' => get_the_title( $post_id ),
		'start' => $start,
		'end'   => ct_clean_date( (string) get_post_meta( $post_id, CT_END, true ) ),
		'city'  => (string) get_post_meta( $post_id, CT_CITY, true ),
	];
}

function ct_format_range( string $start, string $end ): string {
	if ( '' === $end || $end === $start ) {
		return date_i18n( 'j.n.Y', strtotime( $start . ' 12:00' ) );
	}
	return date_i18n( 'j.n.', strtotime( $start . ' 12:00' ) ) . '–' . date_i18n( 'j.n.Y', strtotime( $end . ' 12:00' ) );
}
